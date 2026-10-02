"""Authorize once, pin once, and recheck access before returning evidence."""

import hashlib
import re
import threading
import uuid
from typing import Annotated

import grpc
from fastapi import Query, Request
from fastapi.responses import FileResponse

from retrievec.app.auth import principal
from retrievec.app.errors import APIError
from retrievec.app.schemas import SearchInput
from retrievec.client.rpc import RPCClient
from retrievec.corpus.snapshot import load_snapshot
from retrievec.dense.hybrid import PinnedClient
from retrievec.dense.model import adapter
from retrievec.registry.artifacts import Store


def install_search(app):
    registry, settings = app.state.registry, app.state.settings
    capacity = threading.BoundedSemaphore(2)
    model_lock = threading.Lock()
    model = None

    def encoder():
        nonlocal model
        with model_lock:
            if model is None:
                model = adapter(settings.embedding)
        return model

    @app.post("/api/v1/search")
    def search(value: SearchInput, request: Request):
        user = principal(request)
        # Scope check precedes any RPC, model or artifact access.
        with registry.connect() as db:
            app.state.resources.collection(db, user, value.collection_id)
        if not capacity.acquire(blocking=False):
            raise APIError(503, "search_busy", "Search capacity reached; try again shortly")
        node = None
        try:
            registered = registry.resolve(user, value.collection_id, value.snapshot_id)
            snapshot_id = registered["snapshot_id"]
            modes = (
                ["sparse", "dense", "hybrid"] if value.retrieval == "compare" else [value.retrieval]
            )
            missing = set(modes) - set(registered["capabilities"])
            if missing:
                raise APIError(
                    409,
                    "capability_unavailable",
                    "Select sparse search or ingest a hybrid snapshot",
                )
            store = Store(settings.store)
            node = RPCClient(settings.rpc_address, settings.read_token, principal=user)
            results = {}
            # Request-scoped reuse: immutable artifacts, never authorization decisions.
            artifact_cache = {}
            for mode in modes:
                client = PinnedClient(
                    registry,
                    store,
                    node,
                    user,
                    value.collection_id,
                    mode,
                    None if mode == "sparse" else encoder(),
                    snapshot_id,
                    value.candidates,
                    artifact_cache=artifact_cache,
                )
                results[mode] = client.search(value.query, value.mode, value.top_k, explain=True)
            with registry.connect() as db:
                app.state.resources.collection(db, user, value.collection_id)
                sources = db.execute(
                    "SELECT source_id,paper_id FROM upload_sources WHERE collection_id=%s",
                    (value.collection_id,),
                ).fetchall()
            source_ids = {source["paper_id"]: str(source["source_id"]) for source in sources}
            for result in results.values():
                for hit in result["hits"]:
                    hit["source_id"] = source_ids.get(hit["paper_id"])
            return {
                "snapshot_id": snapshot_id,
                "collection_id": value.collection_id,
                "query": value.query,
                "mode": value.mode,
                "results": results,
            }
        except PermissionError:
            raise
        except grpc.RpcError as error:
            if error.code() == grpc.StatusCode.INVALID_ARGUMENT:
                raise APIError(422, "invalid_query", "Check the structured query syntax") from None
            raise APIError(503, "retrieval_unavailable", "Retrieval service unavailable") from None
        except ValueError:
            raise APIError(
                409, "snapshot_unavailable", "Snapshot or matching model unavailable"
            ) from None
        except OSError:
            raise APIError(
                503, "artifact_unavailable", "Required model or source artifact unavailable"
            ) from None
        finally:
            if node is not None:
                node.close()
            capacity.release()

    @app.get("/api/v1/sources/{source_id}")
    def source(
        source_id: uuid.UUID,
        request: Request,
        snapshot_id: Annotated[str, Query(pattern=r"^rs_[0-9a-f]{64}$")],
    ):
        user = principal(request)
        with registry.connect() as db:
            row = app.state.resources.owned(db, user, "source", source_id)
        try:
            snapshot = registry.resolve(user, row["collection_id"], snapshot_id)
            store = Store(settings.store)
            _, papers, _ = load_snapshot(
                store.path("corpora", snapshot["corpus_snapshot_id"], "ss_")
            )
            if not any(
                paper["paper_id"] == row["paper_id"]
                and paper["source_sha256"] == row["source_hash"]
                for paper in papers
            ):
                raise PermissionError("source not present in pinned snapshot")
            if not re.fullmatch(r"[0-9a-f]{32}\.(pdf|txt|md)", row["storage_key"]):
                raise ValueError("invalid storage key")
            root = (settings.store / "sources").resolve()
            path = root / row["storage_key"]
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("source path outside store")
            with path.open("rb") as file:
                if (
                    path.stat().st_size != row["size_bytes"]
                    or hashlib.file_digest(file, "sha256").hexdigest() != row["source_hash"]
                ):
                    raise ValueError("source integrity mismatch")
            with registry.connect() as db:
                app.state.resources.owned(db, user, "source", source_id)
            return FileResponse(
                path,
                media_type=row["media_type"],
                filename=row["display_name"],
                content_disposition_type="inline",
                headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
            )
        except (OSError, ValueError):
            raise APIError(
                404, "source_unavailable", "Source is unavailable for this snapshot"
            ) from None
