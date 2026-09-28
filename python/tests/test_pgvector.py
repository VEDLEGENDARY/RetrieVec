import os
import tempfile
import unittest
import uuid
from pathlib import Path

from retrievec.corpus.snapshot import load_snapshot, publish_snapshot
from retrievec.dense.artifacts import build_embeddings, load_embeddings
from retrievec.dense.model import FixtureModel
from retrievec.dense.search import exact_search
from retrievec.experiments.pgvector import PgvectorIndex, VectorConfig, build, initialize
from retrievec.registry.artifacts import Store
from retrievec.registry.database import Registry


class VectorBoundaryTests(unittest.TestCase):
    def test_invalid_configuration(self):
        for kwargs in ({"m": 0}, {"ef_construction": 1}, {"max_vectors": True}, {"ef_search": 0}):
            with self.assertRaises(ValueError):
                VectorConfig(**kwargs)


@unittest.skipUnless(os.getenv("RETRIEVEC_VECTOR_TEST_DSN"), "requires isolated pgvector database")
class VectorDatabaseTests(unittest.TestCase):
    def test_immutable_backfill_exact_parity_ann_and_scope(self):
        registry = Registry(os.environ["RETRIEVEC_VECTOR_TEST_DSN"])
        registry.migrate()
        initialize(registry)
        owner, collection = "owner-" + uuid.uuid4().hex, "vector-" + uuid.uuid4().hex
        registry.create_collection(owner, collection)
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            _, papers, chunks = load_snapshot(
                next((root / "datasets/fixtures/snapshots").iterdir())
            )
            for chunk in chunks:
                chunk["collection_id"] = collection
            corpus = publish_snapshot(store.root / "corpora", papers, chunks, collection, {})
            model = FixtureModel()
            embedding_id = build_embeddings(store, corpus, model)
            snapshot = store.build(Path(os.environ["RETRIEVEC_ENGINE"]), corpus, embedding_id)
            registry.register(owner, store.manifest(snapshot))
            registry.ready(owner, collection, snapshot)
            registry.activate(owner, collection, snapshot, None)
            index_id = build(registry, store, owner, collection, snapshot)
            self.assertEqual(build(registry, store, owner, collection, snapshot), index_id)
            index = PgvectorIndex(registry, owner, collection, snapshot, index_id)
            embedding, vectors = load_embeddings(store, embedding_id, corpus.name)
            query = model.encode(["retrieval"])[0]
            limit = len(embedding["chunks"])
            reference = exact_search(
                vectors, [c["chunk_id"] for c in embedding["chunks"]], query, limit
            )
            exact = index.search(query, configuration=model.config, top_k=limit)
            self.assertEqual([r["chunk_id"] for r in reference], [r["chunk_id"] for r in exact])
            for left, right in zip(reference, exact, strict=True):
                self.assertAlmostEqual(left["cosine_score"], right["cosine_score"], places=6)
            approximate = index.search(
                query, configuration=model.config, approximate=True, top_k=limit
            )
            self.assertEqual({r["chunk_id"] for r in approximate}, {r["chunk_id"] for r in exact})
            with self.assertRaises(ValueError):
                index.search(query, configuration={"model": "wrong"})
            denied = PgvectorIndex(registry, "stranger", collection, snapshot, index_id)
            with self.assertRaises(PermissionError):
                denied.search(query, configuration=model.config)
            with registry.connect() as db:
                db.execute(
                    "UPDATE collections SET archived=true WHERE collection_id=%s", (collection,)
                )
            with self.assertRaises(PermissionError):
                index.search(query, configuration=model.config)
