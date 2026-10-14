"""Bounded original-source storage and transactional ingestion handoff."""

import hashlib
import os
import re
import uuid
from datetime import datetime
from typing import Annotated

import psycopg
from fastapi import Query, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from retrievec.app.auth import principal
from retrievec.app.errors import APIError
from retrievec.app.schemas import Job, PaperSourcePage
from retrievec.corpus.snapshot import canonical, digest
from retrievec.registry.jobs import Jobs
from retrievec.registry.worker import publish_bytes


def display_name(name):
    value = re.sub(r"[\x00-\x1f\x7f/\\<>:\"|?*]", "_", name or "document")
    return value[:180].strip(" .") or "document"


def job_view(job):
    result = {key: job[key] for key in Job.model_fields}
    result["job_id"] = str(result["job_id"])
    return result


class UploadLimit:
    def __init__(self, app, limit):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        size = 0
        limit = self.limit if scope.get("path", "").endswith("/uploads") else 64 * 1024

        async def bounded_receive():
            nonlocal size
            message = await receive()
            size += len(message.get("body", b""))
            if size > limit:
                raise APIError(413, "upload_too_large", "Upload exceeds the batch limit")
            return message

        await self.app(scope, bounded_receive, send)


async def stage_file(upload, settings):
    name = display_name(upload.filename)
    extension = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in (".pdf", ".txt", ".md"):
        raise APIError(415, "unsupported_type", "Upload text-based PDF, UTF-8 text or Markdown")
    source_id = uuid.uuid4()
    key = source_id.hex + extension
    root = settings.store / "sources"
    root.mkdir(parents=True, exist_ok=True)
    path = root / key
    size, checksum = 0, hashlib.sha256()
    try:
        with path.open("xb") as file:
            while chunk := await upload.read(64 * 1024):
                if size == 0 and extension == ".pdf" and not chunk.startswith(b"%PDF-"):
                    raise APIError(415, "invalid_pdf", "File does not have a PDF signature")
                size += len(chunk)
                if size > settings.max_file_bytes:
                    raise APIError(413, "file_too_large", "File exceeds the configured size limit")
                checksum.update(chunk)
                file.write(chunk)
            file.flush()
            os.fsync(file.fileno())
        if not size:
            raise APIError(422, "empty_file", "The uploaded file is empty")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return {
        "source_id": source_id,
        "storage_key": key,
        "display_name": name,
        "media_type": "application/pdf" if extension == ".pdf" else "text/plain",
        "size_bytes": size,
        "source_hash": checksum.hexdigest(),
        "paper_id": source_id.hex,
    }


def enqueue_uploads(app, user, collection, key, staged):
    from retrievec.app.admission import lock_admission, require_capacity

    settings, registry = app.state.settings, app.state.registry
    policy = app.state.resources
    with registry.connect() as db:
        lock_admission(db, user)
        current = policy.collection(db, user, collection, manage=True, lock=True)
        require_capacity(db, settings.max_pending_work)
        active = db.execute(
            "SELECT count(*) AS n FROM ingestion_jobs j JOIN collections c "
            "USING(collection_id) WHERE c.owner_id=%s "
            "AND j.state IN ('queued','running','retry_wait')",
            (user,),
        ).fetchone()["n"]
        used = db.execute(
            "SELECT coalesce(sum(size_bytes),0) AS n FROM upload_sources WHERE owner_id=%s", (user,)
        ).fetchone()["n"]
        if used + sum(source["size_bytes"] for source in staged) > settings.storage_quota:
            raise APIError(413, "storage_quota", "Private storage quota reached")
        if active >= settings.max_pending_jobs:
            raise APIError(429, "job_quota", "Wait for pending uploads to finish")
        existing_job = db.execute(
            "SELECT * FROM ingestion_jobs WHERE collection_id=%s AND idempotency_key=%s",
            (collection, key),
        ).fetchone()
        if existing_job:
            raise APIError(
                409, "duplicate_upload", "This upload was already submitted; refresh jobs"
            )
        busy = db.execute(
            "SELECT 1 FROM ingestion_jobs WHERE collection_id=%s "
            "AND state IN ('queued','running','retry_wait')",
            (collection,),
        ).fetchone()
        if busy:
            raise APIError(409, "collection_busy", "Wait for this collection's current upload")
        previous = db.execute(
            "SELECT s.* FROM upload_sources s JOIN ingestion_jobs j USING(job_id) "
            "WHERE s.collection_id=%s AND j.state='succeeded' ORDER BY s.source_id",
            (collection,),
        ).fetchall()
        if current["active_snapshot"] and not previous:
            raise APIError(
                409, "legacy_sources", "Import legacy sources into a new upload collection"
            )
        sources = [
            {
                "paper_id": row["paper_id"],
                "title": row["display_name"],
                "authors": [],
                "path": row["storage_key"],
                "source_url": None,
                "source_sha256": row["source_hash"],
                "license_note": "Private user upload",
            }
            for row in [*previous, *staged]
        ]
        raw = canonical({"schema_version": 1, "sources": sources})
        manifest_hash = digest(raw)
        publish_bytes(settings.store / "inputs" / (manifest_hash + ".json"), raw)
        job = Jobs(registry, user).enqueue(
            collection,
            key,
            {"manifest_hash": manifest_hash},
            {"token_budget": 96, "embedding": settings.embedding, "private_upload": True},
            connection=db,
        )
        for row in staged:
            db.execute(
                "INSERT INTO upload_sources(source_id,collection_id,owner_id,storage_key,"
                "display_name,media_type,size_bytes,source_hash,paper_id,job_id) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["source_id"],
                    collection,
                    user,
                    row["storage_key"],
                    row["display_name"],
                    row["media_type"],
                    row["size_bytes"],
                    row["source_hash"],
                    row["paper_id"],
                    job["job_id"],
                ),
            )
        return job_view(job)


def install_uploads(app):
    settings = app.state.settings
    app.add_middleware(
        UploadLimit, limit=settings.max_file_bytes * settings.max_files + 1024 * 1024
    )

    @app.get("/api/v1/collections/{collection_id}/papers", response_model=PaperSourcePage)
    def papers(
        collection_id: str,
        request: Request,
        q: Annotated[str, Query(max_length=120)] = "",
        after: Annotated[str | None, Query(max_length=96)] = None,
        limit: Annotated[int, Query(ge=1, le=50)] = 25,
    ):
        user = principal(request)
        cursor = None
        if after is not None:
            try:
                stamp, identity = after.split("|")
                timestamp = datetime.fromisoformat(stamp)
                if timestamp.tzinfo is None:
                    raise ValueError("cursor needs a timezone")
                cursor = (timestamp, uuid.UUID(identity))
            except ValueError:
                raise APIError(
                    422, "invalid_cursor", "Refresh the paper library to restart paging"
                ) from None
        with app.state.registry.connect() as db:
            # Recheck live collection access before revealing even a filename.
            app.state.resources.collection(db, user, collection_id)
            where = "WHERE s.collection_id=%s AND strpos(lower(s.display_name),lower(%s))>0 "
            parameters = (collection_id, q)
            if cursor:
                where += "AND (s.created_at,s.source_id)<(%s,%s) "
                parameters += cursor
            rows = db.execute(
                "SELECT s.source_id,s.display_name,s.media_type,s.size_bytes,s.created_at,j.state "
                "FROM upload_sources s JOIN ingestion_jobs j USING(job_id) "
                + where
                + "ORDER BY s.created_at DESC,s.source_id DESC LIMIT %s",
                (*parameters, limit + 1),
            ).fetchall()
            items = rows[:limit]
            return {
                "items": [dict(row) | {"source_id": str(row["source_id"])} for row in items],
                "next_cursor": f"{items[-1]['created_at'].isoformat()}|{items[-1]['source_id']}"
                if len(rows) > limit
                else None,
            }

    @app.post("/api/v1/collections/{collection_id}/uploads", status_code=202, response_model=Job)
    async def upload(collection_id: str, request: Request):
        user = principal(request)

        def authorize():
            with app.state.registry.connect() as db:
                app.state.resources.collection(db, user, collection_id, manage=True)

        await run_in_threadpool(authorize)
        key = request.headers.get("idempotency-key", "")
        if not 1 <= len(key) <= 128:
            raise APIError(422, "idempotency_required", "Supply an upload idempotency key")
        staged = []
        accepted = False
        try:
            async with request.form(max_files=settings.max_files, max_fields=0) as form:
                files = form.getlist("files")
                if not files or any(not isinstance(file, UploadFile) for file in files):
                    raise APIError(422, "files_required", "Select one or more files")
                for file in files:
                    staged.append(await stage_file(file, settings))
            result = await run_in_threadpool(enqueue_uploads, app, user, collection_id, key, staged)
            accepted = True
            return result
        except (psycopg.OperationalError, psycopg.InterfaceError):
            # COMMIT may have succeeded before its acknowledgement was lost. Keep
            # originals so a durable queued job never loses its source files.
            accepted = True
            raise APIError(
                503,
                "upload_unconfirmed",
                "Upload outcome is uncertain; refresh job status before retrying",
            ) from None
        finally:
            if not accepted:
                for row in staged:
                    (settings.store / "sources" / row["storage_key"]).unlink(missing_ok=True)

    @app.get("/api/v1/jobs/{job_id}", response_model=Job)
    def job(job_id: uuid.UUID, request: Request):
        user = principal(request)
        with app.state.registry.connect() as db:
            return job_view(app.state.resources.owned(db, user, "job", job_id))

    @app.get("/api/v1/collections/{collection_id}/jobs", response_model=list[Job])
    def jobs(collection_id: str, request: Request):
        user = principal(request)
        with app.state.registry.connect() as db:
            app.state.resources.collection(db, user, collection_id, manage=True)
            rows = db.execute(
                "SELECT * FROM ingestion_jobs WHERE collection_id=%s "
                "ORDER BY available_at DESC LIMIT 50",
                (collection_id,),
            ).fetchall()
            return [job_view(row) for row in rows]
