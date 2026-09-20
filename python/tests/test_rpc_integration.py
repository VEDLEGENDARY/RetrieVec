import os
import queue
import subprocess
import tempfile
import threading
import unittest
import uuid
from pathlib import Path

import grpc
from retrievallab.client.rpc import RPCClient
from retrievallab.corpus.snapshot import load_snapshot, publish_snapshot
from retrievallab.dense.artifacts import build_embeddings, load_embeddings
from retrievallab.dense.hybrid import PinnedClient
from retrievallab.dense.model import FixtureModel
from retrievallab.registry.artifacts import Store, prepare
from retrievallab.registry.database import Conflict, Registry

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.environ.get("RETRIEVALLAB_TEST_DSN"), "requires isolated PostgreSQL 18")
class RPCIntegrationTests(unittest.TestCase):
    def test_live_rpc_hybrid_activation_restart_and_failure(self):
        engine = Path(os.environ["RETRIEVALLAB_ENGINE"])
        registry = Registry(os.environ["RETRIEVALLAB_TEST_DSN"])
        registry.migrate()
        principal, collection = "owner-" + uuid.uuid4().hex, "collection-" + uuid.uuid4().hex
        registry.create_collection(principal, collection)
        read_token, worker_token = uuid.uuid4().hex, uuid.uuid4().hex
        environment = {
            **os.environ,
            "RETRIEVALLAB_DSN": registry.dsn,
            "RETRIEVALLAB_PRINCIPAL": principal,
            "RETRIEVALLAB_READ_TOKEN": read_token,
            "RETRIEVALLAB_WORKER_TOKEN": worker_token,
        }

        def start(root):
            process = subprocess.Popen(
                [str(engine), "rpc", "--store", str(root), "--listen", "127.0.0.1:0"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=environment,
            )
            lines = queue.Queue()
            threading.Thread(
                target=lambda: lines.put(process.stdout.readline()), daemon=True
            ).start()
            try:
                line = lines.get(timeout=25).strip()
                self.assertTrue(line.startswith("listening grpc://"), line)
                return process, line.removeprefix("listening grpc://")
            except BaseException:
                process.terminate()
                process.communicate(timeout=10)
                raise

        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            _, papers, chunks = load_snapshot(
                next((ROOT / "datasets/fixtures/snapshots").iterdir())
            )
            for chunk in chunks:
                chunk["collection_id"] = collection
            corpus = publish_snapshot(store.root / "corpora", papers, chunks, collection, {})
            model = FixtureModel()
            embedding = build_embeddings(store, corpus, model)
            self.assertEqual(embedding, build_embeddings(store, corpus, model))
            sparse_id = store.build(engine, corpus)
            hybrid_id = store.build(engine, corpus, embedding)
            process, address = start(store.root)
            reader, worker = RPCClient(address, read_token), RPCClient(address, worker_token)
            try:
                registry.register(principal, store.manifest(sparse_id))
                with self.assertRaises(grpc.RpcError) as denied:
                    reader.prepare(collection, sparse_id)
                self.assertEqual(denied.exception.code(), grpc.StatusCode.PERMISSION_DENIED)
                prepare(registry, store, principal, sparse_id, worker)
                registry.activate(principal, collection, sparse_id, None)
                pinned = PinnedClient(registry, store, reader, principal, collection, "sparse")
                before = pinned.search("retrieval")["hits"]
                prepare(registry, store, principal, hybrid_id, worker)
                registry.activate(principal, collection, hybrid_id, sparse_id)
                self.assertEqual(before, pinned.search("retrieval")["hits"])
                self.assertEqual(pinned.snapshot_id, sparse_id)
                hybrid = PinnedClient(
                    registry, store, reader, principal, collection, "hybrid", model
                )
                first = hybrid.search("retrieval")["hits"]
                self.assertTrue(first)
                with self.assertRaises(ValueError):
                    hybrid.search("retrieval AND dense", "structured")
                with self.assertRaises(Conflict):
                    registry.activate(principal, collection, sparse_id, None)
                with self.assertRaises(grpc.RpcError):
                    reader.info("wrong-collection", hybrid_id)
                manifest_path = store.path("embeddings", embedding, "em_") / "vectors.f32"
                del hybrid
                vector_bytes = manifest_path.read_bytes()
                manifest_path.write_bytes(vector_bytes[:-4])
                with self.assertRaises(ValueError):
                    load_embeddings(store, embedding, corpus.name)
                manifest_path.write_bytes(vector_bytes)
            finally:
                reader.close()
                worker.close()
                process.terminate()
                process.communicate(timeout=10)
            process, address = start(store.root)
            reader = RPCClient(address, read_token)
            try:
                repeated = PinnedClient(
                    registry, store, reader, principal, collection, "hybrid", model
                ).search("retrieval")["hits"]
                self.assertEqual(first, repeated)
            finally:
                reader.close()
                process.terminate()
                process.communicate(timeout=10)
