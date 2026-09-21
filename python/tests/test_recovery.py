"""Recovery scenarios use isolated schemas and explicit database-time lease expiry."""

import multiprocessing
import os
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb
from retrievec.app.run_state import RunState
from retrievec.registry.database import Conflict, Registry
from retrievec.registry.jobs import Jobs, LeaseLost
from retrievec.registry.scheduling import heavy_slot
from retrievec.registry.worker import publish_bytes


def interrupted_publication(path, signal, after_link):
    original = os.link

    def pause(source, destination):
        if after_link:
            original(source, destination)
        signal.send("ready")
        signal.recv()
        if not after_link:
            original(source, destination)

    with patch("retrievec.registry.worker.os.link", side_effect=pause):
        publish_bytes(Path(path), b"complete immutable output")


@unittest.skipUnless(os.getenv("RETRIEVEC_TEST_DSN"), "requires isolated PostgreSQL 18")
class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.dsn = os.environ["RETRIEVEC_TEST_DSN"]
        self.schema = "recovery_" + uuid.uuid4().hex
        with psycopg.connect(self.dsn) as db:
            db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.addCleanup(self.drop_schema)
        self.registry = Registry(make_conninfo(self.dsn, options="-c search_path=" + self.schema))
        self.registry.migrate()
        self.registry.create_collection("owner", "collection")
        self.jobs = Jobs(self.registry, "owner")

    def drop_schema(self):
        with psycopg.connect(self.dsn) as db:
            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))

    def snapshot(self, value):
        identity = self.registry.register(
            "owner",
            {
                "schema_version": 1,
                "collection_id": "collection",
                "corpus_snapshot_id": "ss_" + value * 64,
                "capabilities": ["sparse"],
            },
        )
        self.registry.ready("owner", "collection", identity)
        return identity

    def test_heavy_work_is_exclusive_across_independent_connections(self):
        with heavy_slot(self.registry, "ingestion") as first:
            self.assertTrue(first)
            with heavy_slot(self.registry, "research") as second:
                self.assertFalse(second)
        with heavy_slot(self.registry, "research") as next_worker:
            self.assertTrue(next_worker)

    def test_heavy_slot_releases_after_exception(self):
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            with heavy_slot(self.registry, "research"):
                raise RuntimeError("interrupted")
        with heavy_slot(self.registry, "ingestion") as acquired:
            self.assertTrue(acquired)

    def test_admission_contention_rejects_without_holding_up_other_requests(self):
        from retrievec.app.admission import lock_admission
        from retrievec.app.errors import APIError

        with self.registry.connect() as first:
            lock_admission(first, "owner")
            with self.registry.connect() as second:
                second.execute("SET LOCAL statement_timeout='1s'")
                with self.assertRaises(APIError) as caught:
                    lock_admission(second, "owner")
                self.assertEqual(caught.exception.status, 429)
                self.assertEqual(caught.exception.code, "workspace_busy")
        with self.registry.connect() as next_request:
            lock_admission(next_request, "owner")

    def test_combined_queue_limit_counts_ingestion_and_generation(self):
        from retrievec.app.admission import lock_admission, require_capacity
        from retrievec.app.errors import APIError

        self.jobs.enqueue("collection", "queued", {}, {})
        self.make_run()
        with self.registry.connect() as db:
            lock_admission(db, "owner")
            with self.assertRaises(APIError) as caught:
                require_capacity(db, 2)
            self.assertEqual(caught.exception.code, "workspace_capacity")
            require_capacity(db, 3)

    def expire(self, table, key, identity):
        with self.registry.connect() as db:
            db.execute(
                sql.SQL(
                    "UPDATE {} SET lease_until=clock_timestamp()-interval '1 second' WHERE {}=%s"
                ).format(sql.Identifier(table), sql.Identifier(key)),
                (identity,),
            )

    def test_stale_worker_cannot_publish_prepared_artifacts(self):
        self.jobs.enqueue("collection", "first", {}, {})
        lost = self.jobs.claim()
        first = self.snapshot("a")
        self.expire("ingestion_jobs", "job_id", lost["job_id"])
        replacement = self.jobs.claim()
        with self.assertRaises(LeaseLost):
            self.jobs.complete(lost, first)
        self.jobs.complete(replacement, first)
        with self.assertRaises(LeaseLost):
            self.jobs.complete(replacement, first)
        self.assertEqual(self.registry.resolve("owner", "collection")["snapshot_id"], first)

    def test_competing_activation_preserves_winner(self):
        self.jobs.enqueue("collection", "left", {}, {})
        self.jobs.enqueue("collection", "right", {}, {})
        with ThreadPoolExecutor(max_workers=2) as pool:
            claimed = list(pool.map(lambda _: self.jobs.claim(), range(2)))
        self.assertEqual(len({row["job_id"] for row in claimed}), 2)
        first, second = self.snapshot("a"), self.snapshot("b")
        self.jobs.complete(claimed[0], first)
        with self.assertRaises(Conflict):
            self.jobs.complete(claimed[1], second)
        self.assertEqual(self.registry.resolve("owner", "collection")["snapshot_id"], first)

    def test_exhausted_interrupted_ingestion_stops_retrying(self):
        self.jobs.enqueue("collection", "single", {}, {}, max_attempts=1)
        lost = self.jobs.claim()
        self.expire("ingestion_jobs", "job_id", lost["job_id"])
        self.assertIsNone(self.jobs.claim())
        with self.registry.connect() as db:
            row = db.execute(
                "SELECT state,error_code FROM ingestion_jobs WHERE job_id=%s", (lost["job_id"],)
            ).fetchone()
        self.assertEqual(row, {"state": "failed", "error_code": "attempts_exhausted"})

    def make_run(self):
        snapshot = self.snapshot("a")
        conversation, identity = uuid.uuid4(), uuid.uuid4()
        with self.registry.connect() as db:
            db.execute(
                "INSERT INTO conversations(conversation_id,owner_id,collection_id,title) "
                "VALUES(%s,'owner','collection','Synthetic')",
                (conversation,),
            )
            db.execute(
                "INSERT INTO research_runs(run_id,conversation_id,owner_id,collection_id,"
                "snapshot_id,original_question,effective_query,configuration,state) "
                "VALUES(%s,%s,'owner','collection',%s,'question','question',%s,'queued')",
                (identity, conversation, snapshot, Jsonb({"generation": {"cloud": False}})),
            )
        return identity

    def test_provider_interruption_never_automatically_repeats_call(self):
        identity = self.make_run()
        state = RunState(self.registry)
        lost = state.claim()
        self.assertTrue(state.transition(lost, "generating"))
        self.expire("research_runs", "run_id", identity)
        self.assertIsNone(state.claim())
        self.assertFalse(state.transition(lost, "validating"))
        with self.registry.connect() as db:
            row = db.execute(
                "SELECT state,attempts,error_code FROM research_runs WHERE run_id=%s", (identity,)
            ).fetchone()
        self.assertEqual(
            row, {"state": "failed", "attempts": 1, "error_code": "worker_interrupted"}
        )

    def test_cancel_and_reconnect_never_publish_late_evidence(self):
        identity = self.make_run()
        state = RunState(self.registry)
        run = state.claim()
        state.transition(run, "generating")
        state.cancel("owner", identity)
        self.assertFalse(state.transition(run, "validating"))
        self.assertFalse(state.transition(run, "completed", result={"private": "late"}))
        with self.registry.connect() as db:
            events = db.execute(
                "SELECT event_id,type FROM run_events WHERE run_id=%s ORDER BY event_id",
                (identity,),
            ).fetchall()
            self.assertEqual([event["event_id"] for event in events], [1, 2, 3])
            self.assertEqual(events[-1]["type"], "cancelled")
            self.assertEqual(
                db.execute(
                    "SELECT count(*) AS n FROM evidence_citations WHERE run_id=%s", (identity,)
                ).fetchone()["n"],
                0,
            )


class PublicationRecoveryTests(unittest.TestCase):
    def test_process_kill_before_and_after_publication_allows_safe_retry(self):
        context = multiprocessing.get_context("spawn")
        for after_link in (False, True):
            with self.subTest(after_link=after_link), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "manifest.json"
                parent, child = context.Pipe()
                process = context.Process(
                    target=interrupted_publication, args=(str(path), child, after_link)
                )
                process.start()
                child.close()
                try:
                    self.assertTrue(parent.poll(15), "child did not reach publication boundary")
                    self.assertEqual(parent.recv(), "ready")
                    process.kill()
                    process.join(5)
                    self.assertFalse(process.is_alive())
                    self.assertEqual(path.exists(), after_link)
                    publish_bytes(path, b"complete immutable output")
                    self.assertEqual(path.read_bytes(), b"complete immutable output")
                finally:
                    if process.is_alive():
                        process.kill()
                        process.join(5)
                    parent.close()
                    process.close()

    def test_retry_after_artifact_publication_is_idempotent_and_conflict_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot" / "manifest.json"
            publish_bytes(path, b"published")
            publish_bytes(path, b"published")
            with self.assertRaises(Conflict):
                publish_bytes(path, b"changed")
            self.assertEqual(path.read_bytes(), b"published")
            self.assertEqual(list(path.parent.glob(".publish-*")), [])
