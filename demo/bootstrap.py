"""Preload a real hybrid SciFact snapshot before starting the ordinary workspace."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import grpc
from psycopg.conninfo import make_conninfo
from retrievec.client.rpc import RPCClient
from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import import_manifest
from retrievec.dense.artifacts import build_embeddings
from retrievec.dense.model import adapter
from retrievec.registry.artifacts import Store, publish
from retrievec.registry.database import Registry

private = json.loads(Path("/settings/credentials.json").read_text())
os.environ.update(
    RETRIEVEC_DSN=make_conninfo(
        host="postgres", dbname="retrievec", user="retrievec", password=private["database"]
    ),
    RETRIEVEC_READ_TOKEN=private["read"],
    RETRIEVEC_WORKER_TOKEN=private["worker"],
)
registry = Registry(os.environ["RETRIEVEC_DSN"])
registry.migrate()
owner, collection = "demo-corpus-owner", "scifact-starter"
registry.create_collection(owner, collection)
with registry.connect() as db:
    db.execute(
        "UPDATE collections SET visibility='curated', title=%s "
        "WHERE collection_id=%s AND owner_id=%s",
        ("SciFact starter · 24 abstracts", collection, owner),
    )
try:
    registered = registry.resolve(owner, collection)
except ValueError:
    registered = None
if registered is None or "hybrid" not in registered["capabilities"]:
    store = Store(Path(os.environ["RETRIEVEC_STORE"]))
    engine = Path(os.environ["RETRIEVEC_ENGINE"])
    dataset = Path("/app/datasets/answer_quality")
    corpus = import_manifest(
        dataset / "corpus-manifest.json",
        dataset,
        store.root / "corpora",
        collection,
        96,
        GoAnalyzer(engine),
    )
    embedding = build_embeddings(store, corpus, adapter("minilm"))
    snapshot = store.build(engine, corpus, embedding)
    rpc = subprocess.Popen(
        [str(engine), "rpc", "--store", str(store.root), "--listen", "127.0.0.1:8092"]
    )
    node = RPCClient("127.0.0.1:8092", private["worker"], principal=owner)
    try:
        for attempt in range(30):
            try:
                publish(
                    registry,
                    store,
                    owner,
                    snapshot,
                    registered["snapshot_id"] if registered else None,
                    node,
                )
                break
            except grpc.RpcError:
                if attempt == 29:
                    raise
                time.sleep(0.2)
    finally:
        node.close()
        rpc.terminate()
        rpc.wait(timeout=10)
print("SciFact starter ready. Sign in through local Keycloak; generation is unconfigured.")
os.execv(sys.executable, [sys.executable, "-m", "retrievec.runtime", "workspace"])
