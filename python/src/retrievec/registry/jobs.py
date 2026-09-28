"""Leased, fenced, at-least-once ingestion backed by database time."""

import uuid
from contextlib import nullcontext

from psycopg.types.json import Jsonb

from retrievec.corpus.snapshot import canonical, digest
from retrievec.observability import carrier
from retrievec.registry.database import Conflict, Registry
from retrievec.telemetry import CONTEXT, emit


class LeaseLost(Conflict):
    pass


class Jobs:
    def __init__(self, registry: Registry, principal: str):
        self.registry, self.principal = registry, principal

    def enqueue(
        self,
        collection: str,
        key: str,
        payload: dict,
        configuration: dict,
        max_attempts: int = 3,
        *,
        connection=None,
    ) -> dict:
        if not key or not 1 <= max_attempts <= 10:
            raise ValueError("invalid idempotency key or attempt limit")
        input_hash, config_hash = digest(canonical(payload)), digest(canonical(configuration))
        with (
            nullcontext(connection) if connection is not None else self.registry.connect()
        ) as connection:
            owner = self.registry.authorize(connection, self.principal, collection, lock=True)
            connection.execute(
                (
                    "INSERT INTO "
                    "ingestion_jobs(job_id,collection_id,idempotency_key,input_hash,config_ha"
                    "sh,payload,expected_parent,max_attempts,traceparent) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT DO NOTHING"
                ),
                (
                    uuid.uuid4(),
                    collection,
                    key,
                    input_hash,
                    config_hash,
                    Jsonb({"input": payload, "configuration": configuration}),
                    owner["active_snapshot"],
                    max_attempts,
                    carrier().get("traceparent"),
                ),
            )
            job = connection.execute(
                "SELECT * FROM ingestion_jobs WHERE collection_id=%s AND idempotency_key=%s",
                (collection, key),
            ).fetchone()
            if job["input_hash"] != input_hash or job["config_hash"] != config_hash:
                raise Conflict("idempotency key was used for different input/configuration")
            if not job["request_id"] and CONTEXT.get().get("request_id"):
                connection.execute(
                    "UPDATE ingestion_jobs SET request_id=%s WHERE job_id=%s",
                    (CONTEXT.get()["request_id"], job["job_id"]),
                )
            return job

    def claim(self, lease_seconds: int = 60) -> dict | None:
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("invalid lease duration")
        with self.registry.connect() as connection:
            connection.execute(
                (
                    "UPDATE ingestion_jobs j SET "
                    "state='failed',error_code='attempts_exhausted' FROM collections c WHERE "
                    "j.collection_id=c.collection_id AND c.owner_id=%s AND "
                    "j.attempts>=j.max_attempts AND (j.state IN ('queued','retry_wait') OR "
                    "(j.state='running' AND j.lease_until<clock_timestamp()))"
                ),
                (self.principal,),
            )
            return connection.execute(
                """WITH candidate AS (
              SELECT j.job_id FROM ingestion_jobs j JOIN collections c USING(collection_id)
              WHERE c.owner_id=%s AND NOT c.archived AND j.attempts<j.max_attempts
              AND ((j.state IN ('queued','retry_wait') AND j.available_at<=clock_timestamp())
                   OR (j.state='running' AND j.lease_until<clock_timestamp()))
              ORDER BY j.available_at,j.job_id FOR UPDATE OF j SKIP LOCKED LIMIT 1
            ) UPDATE ingestion_jobs j SET state='running',attempts=j.attempts+1,
              fencing_token=j.fencing_token+1,
              lease_until=clock_timestamp()+(%s * interval '1 second'),
              stage_started_at=clock_timestamp()
              FROM candidate WHERE j.job_id=candidate.job_id RETURNING j.*""",
                (self.principal, lease_seconds),
            ).fetchone()

    def checkpoint(self, job: dict, stage: str, progress: dict, lease_seconds: int = 60) -> None:
        if (
            stage not in ("extract", "chunk", "sparse_build", "embed", "validate", "activate")
            or not 1 <= lease_seconds <= 3600
        ):
            raise ValueError("invalid stage or lease")
        with self.registry.connect() as connection:
            self.registry.authorize(connection, self.principal, job["collection_id"])
            prior = connection.execute(
                "SELECT stage,extract(epoch FROM (clock_timestamp()-stage_started_at))*1000 "
                "AS elapsed_ms FROM ingestion_jobs WHERE job_id=%s AND fencing_token=%s "
                "AND state='running' AND lease_until>clock_timestamp() FOR UPDATE",
                (job["job_id"], job["fencing_token"]),
            ).fetchone()
            if prior is None:
                raise LeaseLost("job lease is no longer current")
            row = connection.execute(
                (
                    "UPDATE ingestion_jobs SET "
                    "stage=%s,progress=%s,stage_started_at=clock_timestamp(),"
                    "lease_until=clock_timestamp()+(%s * interval '1 "
                    "second') WHERE job_id=%s AND fencing_token=%s AND state='running' AND "
                    "lease_until>clock_timestamp() RETURNING job_id"
                ),
                (stage, Jsonb(progress), lease_seconds, job["job_id"], job["fencing_token"]),
            ).fetchone()
            if row is None:
                raise LeaseLost("job lease is no longer current")
        emit(
            "ingestion.stage",
            job_id=job["job_id"],
            stage=prior["stage"],
            elapsed_ms=max(0, float(prior["elapsed_ms"])),
            outcome="completed",
        )

    def heartbeat(self, job: dict, lease_seconds: int = 60) -> None:
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("invalid lease duration")
        with self.registry.connect() as connection:
            self.registry.authorize(connection, self.principal, job["collection_id"])
            row = connection.execute(
                (
                    "UPDATE ingestion_jobs SET lease_until=clock_timestamp()+(%s * interval "
                    "'1 second') WHERE job_id=%s AND fencing_token=%s AND state='running' AND "
                    "lease_until>clock_timestamp() RETURNING job_id"
                ),
                (lease_seconds, job["job_id"], job["fencing_token"]),
            ).fetchone()
            if row is None:
                raise LeaseLost("job lease is no longer current")

    def complete(self, job: dict, snapshot_id: str, *, papers: list[dict] | None = None) -> None:
        with self.registry.connect() as connection:
            # Every path takes the collection lock before a job lock, including archive.
            collection = self.registry.authorize(
                connection, self.principal, job["collection_id"], lock=True
            )
            current = connection.execute(
                (
                    "SELECT * FROM ingestion_jobs WHERE job_id=%s AND fencing_token=%s AND "
                    "state='running' AND lease_until>clock_timestamp() FOR UPDATE"
                ),
                (job["job_id"], job["fencing_token"]),
            ).fetchone()
            if current is None:
                raise LeaseLost("stale worker cannot activate")
            snapshot = connection.execute(
                (
                    "SELECT snapshot_id FROM retrieval_snapshots WHERE snapshot_id=%s AND "
                    "collection_id=%s AND state='ready'"
                ),
                (snapshot_id, current["collection_id"]),
            ).fetchone()
            if snapshot is None or collection["active_snapshot"] not in (
                current["expected_parent"],
                snapshot_id,
            ):
                raise Conflict("snapshot not ready or parent changed")
            if papers is not None:
                connection.execute(
                    "DELETE FROM collection_papers WHERE collection_id=%s",
                    (current["collection_id"],),
                )
                for paper in papers:
                    connection.execute(
                        (
                            "INSERT INTO "
                            "paper_versions(paper_version_id,paper_id,source_sha256,provenance) "
                            "VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING"
                        ),
                        (
                            paper["paper_version_id"],
                            paper["paper_id"],
                            paper["source_sha256"],
                            Jsonb(paper),
                        ),
                    )
                    connection.execute(
                        (
                            "INSERT INTO collection_papers"
                            "(collection_id,paper_id,paper_version_id) "
                            "VALUES(%s,%s,%s)"
                        ),
                        (current["collection_id"], paper["paper_id"], paper["paper_version_id"]),
                    )
            connection.execute(
                "UPDATE collections SET active_snapshot=%s WHERE collection_id=%s",
                (snapshot_id, current["collection_id"]),
            )
            connection.execute(
                (
                    "UPDATE ingestion_jobs SET "
                    "state='succeeded',stage='activate',output_snapshot=%s,lease_until=NULL "
                    "WHERE job_id=%s"
                ),
                (snapshot_id, current["job_id"]),
            )
        emit(
            "ingestion.activated",
            job_id=job["job_id"],
            snapshot_id=snapshot_id,
            collection_id=job["collection_id"],
            attempt=job["attempts"],
        )

    def fail(self, job: dict, code: str, *, retry: bool) -> None:
        if code not in (
            "invalid_input",
            "unavailable",
            "stale_parent",
            "embedding_failed",
            "extraction_timeout",
            "encrypted_pdf",
            "ocr_required",
        ):
            raise ValueError("unsafe or unknown failure code")
        with self.registry.connect() as connection:
            self.registry.authorize(connection, self.principal, job["collection_id"])
            row = connection.execute(
                (
                    "UPDATE ingestion_jobs SET state=CASE WHEN %s AND attempts<max_attempts "
                    "THEN 'retry_wait' ELSE 'failed' "
                    "END,error_code=%s,lease_until=NULL,available_at=clock_timestamp()+(least"
                    "(300,power(2,attempts)) * interval '1 second') WHERE job_id=%s AND "
                    "fencing_token=%s AND state='running' AND lease_until>clock_timestamp() "
                    "RETURNING job_id"
                ),
                (retry, code, job["job_id"], job["fencing_token"]),
            ).fetchone()
            if row is None:
                raise LeaseLost("stale worker cannot finalize")

    def cancel(self, collection: str, job_id: str) -> None:
        with self.registry.connect() as connection:
            self.registry.authorize(connection, self.principal, collection)
            connection.execute(
                (
                    "UPDATE ingestion_jobs SET "
                    "state='cancelled',lease_until=NULL,fencing_token=fencing_token+1 WHERE "
                    "job_id=%s AND collection_id=%s AND state NOT IN "
                    "('succeeded','failed','cancelled')"
                ),
                (job_id, collection),
            )
