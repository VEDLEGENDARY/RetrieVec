"""Resource policy is checked from live metadata on every request."""

import uuid

from fastapi import Request

from retrievec.app.auth import principal
from retrievec.app.schemas import Collection, CollectionInput


def collection_view(row, user):
    return {
        key: row[key] for key in ("collection_id", "title", "visibility", "active_snapshot")
    } | {"can_manage": row["owner_id"] == user}


class Resources:
    def __init__(self, registry):
        self.registry = registry

    def collection(self, db, user, collection, *, manage=False, lock=False):
        return self.registry.authorize(db, user, collection, read=not manage, lock=lock)

    def owned(self, db, user, kind, identity):
        # Fixed queries prevent resource kinds from becoming arbitrary SQL identifiers.
        queries = {
            "conversation": "SELECT r.* FROM conversations r "
            "JOIN collections c USING(collection_id) "
            "WHERE r.conversation_id=%s AND r.owner_id=%s AND NOT c.archived "
            "AND (c.owner_id=r.owner_id OR c.visibility='curated')",
            "job": "SELECT j.* FROM ingestion_jobs j JOIN collections c USING(collection_id) "
            "WHERE j.job_id=%s AND c.owner_id=%s AND NOT c.archived",
            "source": "SELECT s.* FROM upload_sources s JOIN collections c USING(collection_id) "
            "WHERE s.source_id=%s AND NOT c.archived "
            "AND (c.owner_id=%s OR c.visibility='curated')",
            "run": "SELECT r.* FROM research_runs r JOIN collections c USING(collection_id) "
            "WHERE r.run_id=%s AND r.owner_id=%s AND NOT c.archived "
            "AND (c.owner_id=r.owner_id OR c.visibility='curated')",
            "citation": "SELECT e.* FROM evidence_citations e JOIN research_runs r USING(run_id) "
            "JOIN collections c ON c.collection_id=r.collection_id "
            "WHERE e.citation_id=%s AND r.owner_id=%s AND NOT c.archived "
            "AND (c.owner_id=r.owner_id OR c.visibility='curated')",
            "export": "SELECT e.* FROM exports e JOIN research_runs r USING(run_id) "
            "JOIN collections c ON c.collection_id=r.collection_id "
            "WHERE e.export_id=%s AND r.owner_id=%s AND NOT c.archived "
            "AND (c.owner_id=r.owner_id OR c.visibility='curated')",
        }
        row = db.execute(queries[kind], (identity, user)).fetchone()
        if row is None:
            raise PermissionError("resource unavailable")
        return row


def install_resources(app):
    registry = app.state.registry
    policy = Resources(registry)
    app.state.resources = policy

    @app.get("/api/v1/collections", response_model=list[Collection])
    def collections(request: Request):
        user = principal(request)
        with registry.connect() as db:
            rows = db.execute(
                "SELECT * FROM collections WHERE NOT archived AND "
                "(owner_id=%s OR visibility='curated') ORDER BY title,collection_id",
                (user,),
            ).fetchall()
            return [collection_view(row, user) for row in rows]

    @app.post("/api/v1/collections", response_model=Collection, status_code=201)
    def create(request: Request, value: CollectionInput):
        user = principal(request)
        with registry.connect() as db:
            row = db.execute(
                "INSERT INTO collections(collection_id,owner_id,title) VALUES(%s,%s,%s) "
                "RETURNING *",
                (uuid.uuid4().hex, user, value.title),
            ).fetchone()
            return collection_view(row, user)

    @app.patch("/api/v1/collections/{collection_id}", response_model=Collection)
    def rename(collection_id: str, value: CollectionInput, request: Request):
        user = principal(request)
        with registry.connect() as db:
            policy.collection(db, user, collection_id, manage=True, lock=True)
            row = db.execute(
                "UPDATE collections SET title=%s WHERE collection_id=%s RETURNING *",
                (value.title, collection_id),
            ).fetchone()
            return collection_view(row, user)

    @app.delete("/api/v1/collections/{collection_id}", status_code=204)
    def archive(collection_id: str, request: Request):
        user = principal(request)
        with registry.connect() as db:
            policy.collection(db, user, collection_id, manage=True, lock=True)
            db.execute(
                "UPDATE collections SET archived=true WHERE collection_id=%s", (collection_id,)
            )
            db.execute(
                "UPDATE ingestion_jobs SET state='cancelled',fencing_token=fencing_token+1,"
                "lease_until=NULL WHERE collection_id=%s "
                "AND state IN ('queued','retry_wait','running')",
                (collection_id,),
            )
