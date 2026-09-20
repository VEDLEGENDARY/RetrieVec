import os
import unittest
import uuid

from retrievec.registry.database import Conflict, Registry
from retrievec.registry.jobs import Jobs, LeaseLost


@unittest.skipUnless(os.environ.get("RETRIEVEC_TEST_DSN"), "requires isolated PostgreSQL 18")
class RegistryTests(unittest.TestCase):
    def test_job_idempotency_and_stale_fencing(self):
        jobs = Jobs(self.registry, "test-owner")
        first = jobs.enqueue(self.collection, "same", {"source": "x"}, {})
        self.assertEqual(
            first["job_id"], jobs.enqueue(self.collection, "same", {"source": "x"}, {})["job_id"]
        )
        with self.assertRaises(Conflict):
            jobs.enqueue(self.collection, "same", {"source": "changed"}, {})
        claimed = jobs.claim()
        self.assertIsNotNone(claimed)
        with self.registry.connect() as connection:
            connection.execute(
                (
                    "UPDATE ingestion_jobs SET lease_until=clock_timestamp()-interval '1 "
                    "second' WHERE job_id=%s"
                ),
                (claimed["job_id"],),
            )
        replacement = jobs.claim()
        self.assertGreater(replacement["fencing_token"], claimed["fencing_token"])
        with self.assertRaises(LeaseLost):
            jobs.checkpoint(claimed, "extract", {})
        jobs.checkpoint(replacement, "extract", {})
        jobs.cancel(replacement["collection_id"], str(replacement["job_id"]))
        with self.assertRaises(LeaseLost):
            jobs.heartbeat(replacement)

    def setUp(self):
        self.registry = Registry(os.environ["RETRIEVEC_TEST_DSN"])
        self.registry.migrate()
        self.collection = "test-" + uuid.uuid4().hex
        self.registry.create_collection("test-owner", self.collection)

    def test_owner_ready_and_parent_cas(self):
        with self.assertRaises(PermissionError):
            self.registry.create_collection("other-owner", self.collection)

        def make(corpus):
            return {
                "schema_version": 1,
                "collection_id": self.collection,
                "corpus_snapshot_id": "ss_" + corpus * 64,
                "capabilities": ["sparse"],
            }

        first = self.registry.register("test-owner", make("a"))
        second = self.registry.register("test-owner", make("b"))
        with self.assertRaises(Conflict):
            self.registry.activate("test-owner", self.collection, first, None)
        self.registry.ready("test-owner", self.collection, first)
        self.registry.ready("test-owner", self.collection, second)
        self.registry.activate("test-owner", self.collection, first, None)
        self.registry.activate("test-owner", self.collection, first, None)
        with self.assertRaises(Conflict):
            self.registry.activate("test-owner", self.collection, second, None)
        self.assertEqual(self.registry.resolve("test-owner", self.collection)["snapshot_id"], first)
