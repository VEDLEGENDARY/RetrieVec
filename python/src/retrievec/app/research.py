"""Owned, immutable research requests. Replays always create a new run."""

import json
import uuid
from typing import Literal

from fastapi import Header, Query, Request
from fastapi.responses import Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field

from retrievec.app.auth import principal
from retrievec.app.errors import APIError
from retrievec.app.generation import load_providers
from retrievec.corpus.snapshot import canonical, digest
from retrievec.registry.artifacts import Store
from retrievec.registry.database import Conflict


class ConversationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    collection_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=120)


class RunInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=4096)
    effective_query: str | None = Field(default=None, min_length=1, max_length=4096)
    snapshot: Literal["current", "historical"] = "current"
    parent_run: uuid.UUID | None = None
    retrieval: Literal["sparse", "dense", "hybrid"] = "hybrid"
    provider: str = Field(default="local", pattern=r"^[a-zA-Z0-9_-]{1,64}$")


def run_view(row):
    return {
        key: row[key]
        for key in (
            "run_id",
            "conversation_id",
            "collection_id",
            "snapshot_id",
            "original_question",
            "effective_query",
            "configuration",
            "state",
            "parent_run",
            "result",
            "error_code",
            "created_at",
        )
    }


def install_research(app):
    registry, policy = app.state.registry, app.state.resources
    app.state.providers = load_providers(app.state.settings.generation_config)

    @app.post("/api/v1/runs/{run_id}/cancel", status_code=204)
    def cancel(run_id: uuid.UUID, request: Request):
        from retrievec.app.run_state import RunState

        RunState(registry).cancel(principal(request), run_id)

    @app.get("/api/v1/runs/{run_id}/events")
    def events(
        run_id: uuid.UUID,
        request: Request,
        after: int = Query(default=0, ge=0),
        last_event_id: str | None = Header(default=None, pattern=r"^[0-9]{1,18}$"),
    ):
        # Finite resumable SSE batches: each reconnect rechecks the live session and resource.
        after = max(after, int(last_event_id or "0"))
        with registry.connect() as db:
            policy.owned(db, principal(request), "run", run_id)
            rows = db.execute(
                "SELECT event_id,type,payload FROM run_events WHERE run_id=%s "
                "AND event_id>%s ORDER BY event_id LIMIT 100",
                (run_id, after),
            ).fetchall()
        body = "retry: 1500\n\n" + "".join(
            f"id: {row['event_id']}\nevent: {row['type']}\ndata: "
            + json.dumps({"run_id": str(run_id), **row["payload"]})
            + "\n\n"
            for row in rows
        )
        return Response(body, media_type="text/event-stream", headers={"Cache-Control": "no-store"})

    @app.get("/api/v1/collections/{collection_id}/providers")
    def providers(collection_id: str, request: Request):
        with registry.connect() as db:
            policy.collection(db, principal(request), collection_id)
            consents = {
                row["provider_hash"]
                for row in db.execute(
                    "SELECT provider_hash FROM provider_consents WHERE collection_id=%s",
                    (collection_id,),
                ).fetchall()
            }
            return [
                {
                    **provider.public(),
                    "identity": provider.identity,
                    "consented": not provider.cloud or provider.identity in consents,
                }
                for provider in app.state.providers.values()
            ]

    @app.put(
        "/api/v1/collections/{collection_id}/providers/{provider_name}/consent", status_code=204
    )
    def consent(collection_id: str, provider_name: str, request: Request):
        user = principal(request)
        with registry.connect() as db:
            policy.collection(db, user, collection_id, manage=True, lock=True)
            provider = app.state.providers.get(provider_name)
            if provider is None:
                raise APIError(404, "provider_unavailable", "Provider is not configured")
            db.execute(
                "INSERT INTO provider_consents(collection_id,provider_hash,granted_by) "
                "VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                (collection_id, provider.identity, user),
            )

    @app.delete(
        "/api/v1/collections/{collection_id}/providers/{provider_name}/consent", status_code=204
    )
    def revoke_consent(collection_id: str, provider_name: str, request: Request):
        with registry.connect() as db:
            policy.collection(db, principal(request), collection_id, manage=True, lock=True)
            provider = app.state.providers.get(provider_name)
            if provider is None:
                raise APIError(404, "provider_unavailable", "Provider is not configured")
            db.execute(
                "DELETE FROM provider_consents WHERE collection_id=%s AND provider_hash=%s",
                (collection_id, provider.identity),
            )
            from retrievec.app.run_state import event

            rows = db.execute(
                "UPDATE research_runs SET state='cancelled',fencing_token=fencing_token+1,"
                "lease_until=NULL WHERE collection_id=%s AND configuration->>'provider_hash'=%s "
                "AND state IN ('queued','retrieving','generating','validating') RETURNING run_id",
                (collection_id, provider.identity),
            ).fetchall()
            for row in rows:
                event(db, row["run_id"], "cancelled")

    @app.post("/api/v1/conversations", status_code=201)
    def create(value: ConversationInput, request: Request):
        user = principal(request)
        with registry.connect() as db:
            policy.collection(db, user, value.collection_id, lock=True)
            return db.execute(
                "INSERT INTO conversations(conversation_id,owner_id,collection_id,title) "
                "VALUES(%s,%s,%s,%s) RETURNING *",
                (uuid.uuid4(), user, value.collection_id, value.title.strip()),
            ).fetchone()

    @app.get("/api/v1/collections/{collection_id}/conversations")
    def conversations(collection_id: str, request: Request):
        user = principal(request)
        with registry.connect() as db:
            policy.collection(db, user, collection_id)
            return db.execute(
                "SELECT * FROM conversations WHERE collection_id=%s AND owner_id=%s "
                "ORDER BY created_at DESC LIMIT 100",
                (collection_id, user),
            ).fetchall()

    @app.get("/api/v1/conversations/{conversation_id}/runs")
    def history(conversation_id: uuid.UUID, request: Request):
        user = principal(request)
        with registry.connect() as db:
            policy.owned(db, user, "conversation", conversation_id)
            return [
                run_view(row)
                for row in db.execute(
                    "SELECT * FROM research_runs WHERE conversation_id=%s "
                    "ORDER BY created_at DESC LIMIT 100",
                    (conversation_id,),
                ).fetchall()
            ]

    @app.get("/api/v1/runs/{run_id}")
    def read(run_id: uuid.UUID, request: Request):
        with registry.connect() as db:
            return run_view(policy.owned(db, principal(request), "run", run_id))

    @app.post("/api/v1/conversations/{conversation_id}/runs", status_code=202)
    def enqueue(
        conversation_id: uuid.UUID,
        value: RunInput,
        request: Request,
        idempotency_key: str = Header(min_length=1, max_length=128),
    ):
        user = principal(request)
        request_hash = digest(canonical(value.model_dump(mode="json")))
        with registry.connect() as db:
            conversation = policy.owned(db, user, "conversation", conversation_id)
            collection = policy.collection(db, user, conversation["collection_id"], lock=True)
            existing = db.execute(
                "SELECT * FROM research_runs WHERE owner_id=%s AND conversation_id=%s "
                "AND idempotency_key=%s",
                (user, conversation_id, idempotency_key),
            ).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise Conflict("idempotency key reused with different request")
                return run_view(existing)
            parent = None
            if value.parent_run:
                parent = policy.owned(db, user, "run", value.parent_run)
                if parent["conversation_id"] != conversation_id:
                    raise APIError(422, "invalid_parent", "Choose a run from this conversation")
            if value.snapshot == "historical" and parent is None:
                raise APIError(422, "invalid_snapshot", "Historical replay requires a parent run")
            pinned = (
                parent["snapshot_id"]
                if value.snapshot == "historical"
                else collection["active_snapshot"]
            )
            snapshot = db.execute(
                "SELECT * FROM retrieval_snapshots WHERE collection_id=%s AND snapshot_id=%s "
                "AND state='ready'",
                (collection["collection_id"], pinned),
            ).fetchone()
            if not snapshot:
                raise APIError(409, "snapshot_unavailable", "Ingest sources before creating a run")
            try:
                if Store(app.state.settings.store).manifest(pinned) != snapshot["manifest"]:
                    raise ValueError("manifest mismatch")
            except (OSError, ValueError):
                raise APIError(
                    409, "artifact_unavailable", "Retained snapshot is unavailable"
                ) from None
            if value.retrieval not in snapshot["capabilities"]:
                raise APIError(409, "capability_unavailable", "Select an available retrieval mode")
            # Serialize per-user quota across all owned conversations and collections.
            db.execute(
                "SELECT principal_id FROM principals WHERE principal_id=%s FOR UPDATE", (user,)
            )
            pending = db.execute(
                "SELECT count(*) AS count FROM research_runs WHERE owner_id=%s "
                "AND state IN ('queued','retrieving','generating','validating')",
                (user,),
            ).fetchone()["count"]
            if pending >= 3:
                raise APIError(409, "run_capacity", "Wait for or cancel an active run")
            config = {
                "schema_version": 1,
                "retrieval": value.retrieval,
                "provider": value.provider,
                "top_k": 8,
                "candidates": 100,
                "query_policy": "explicit-standalone-v1",
            }
            provider = app.state.providers.get(value.provider)
            if provider is None:
                raise APIError(
                    409,
                    "provider_unavailable",
                    "Configure a generation provider; search remains available",
                )
            if (
                provider.cloud
                and not db.execute(
                    "SELECT 1 FROM provider_consents WHERE collection_id=%s AND provider_hash=%s",
                    (collection["collection_id"], provider.identity),
                ).fetchone()
            ):
                raise APIError(
                    403, "consent_required", "Collection owner must enable this cloud provider"
                )
            config["generation"] = provider.public()
            config["provider_hash"] = provider.identity
            row = db.execute(
                "INSERT INTO research_runs(run_id,conversation_id,owner_id,collection_id,"
                "snapshot_id,original_question,effective_query,configuration,state,"
                "idempotency_key,request_hash,parent_run) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'queued',%s,%s,%s) RETURNING *",
                (
                    uuid.uuid4(),
                    conversation_id,
                    user,
                    collection["collection_id"],
                    pinned,
                    value.question.strip(),
                    (value.effective_query or value.question).strip(),
                    Jsonb(config),
                    idempotency_key,
                    request_hash,
                    value.parent_run,
                ),
            ).fetchone()
            from retrievec.app.run_state import event

            event(db, row["run_id"], "queued")
            return run_view(row)
