import os
import unittest
import uuid

from retrievallab.registry.database import Conflict, Registry


@unittest.skipUnless(os.environ.get("RETRIEVALLAB_TEST_DSN"), "requires isolated PostgreSQL 18")
class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry(os.environ["RETRIEVALLAB_TEST_DSN"])
        self.registry.migrate()
        self.collection = "test-" + uuid.uuid4().hex
        self.registry.create_collection("test-owner", self.collection)

    def test_owner_ready_and_parent_cas(self):
        with self.assertRaises(PermissionError):
            self.registry.create_collection("other-owner", self.collection)
        def make(corpus):
            return {"schema_version": 1, "collection_id": self.collection, "corpus_snapshot_id": "ss_" + corpus * 64, "capabilities": ["sparse"]}
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
