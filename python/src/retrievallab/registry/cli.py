"""Registry and worker command line; secrets are supplied through the environment."""

import argparse
import json
import os
from pathlib import Path

from retrievallab.client.rpc import RPCClient
from retrievallab.registry.artifacts import Store
from retrievallab.registry.database import Registry
from retrievallab.registry.jobs import Jobs
from retrievallab.registry.worker import Worker, stage_inputs


def main(argv=None):
    parser = argparse.ArgumentParser(prog="retrievallab registry")
    parser.add_argument("--store", type=Path, default=Path("artifacts/store"))
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("migrate")
    create = sub.add_parser("create-collection")
    create.add_argument("collection")
    enqueue = sub.add_parser(
        "enqueue", help="replace collection with the complete supplied source set"
    )
    enqueue.add_argument("--collection", required=True)
    enqueue.add_argument("--key", required=True)
    enqueue.add_argument("--manifest", required=True, type=Path)
    enqueue.add_argument("--source-root", required=True, type=Path)
    enqueue.add_argument("--embedding", choices=("fixture", "minilm"))
    enqueue.add_argument("--token-budget", type=int, default=96)
    worker = sub.add_parser("work-once")
    worker.add_argument("--engine", type=Path, required=True)
    worker.add_argument("--rpc", default="127.0.0.1:8092")
    search = sub.add_parser("search")
    search.add_argument("--collection", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--retrieval", choices=("sparse", "dense", "hybrid"), default="hybrid")
    search.add_argument("--mode", choices=("free_text", "structured"), default="free_text")
    search.add_argument("--embedding", choices=("fixture", "minilm"), default="minilm")
    search.add_argument("--rpc", default="127.0.0.1:8092")
    args = parser.parse_args(argv)
    registry = Registry(os.environ["RETRIEVALLAB_DSN"])
    principal = os.environ["RETRIEVALLAB_PRINCIPAL"]
    store = Store(args.store)
    if args.action == "migrate":
        registry.migrate()
    elif args.action == "create-collection":
        registry.create_collection(principal, args.collection)
    elif args.action == "enqueue":
        payload = stage_inputs(store, args.manifest, args.source_root)
        job = Jobs(registry, principal).enqueue(
            args.collection,
            args.key,
            payload,
            {"token_budget": args.token_budget, "embedding": args.embedding},
        )
        print(job["job_id"])
    elif args.action == "search":
        from retrievallab.dense.hybrid import PinnedClient
        from retrievallab.dense.model import adapter

        node = RPCClient(args.rpc, os.environ["RETRIEVALLAB_READ_TOKEN"])
        try:
            client = PinnedClient(
                registry,
                store,
                node,
                principal,
                args.collection,
                args.retrieval,
                adapter(args.embedding) if args.retrieval != "sparse" else None,
            )
            print(
                json.dumps(
                    client.search(args.query, args.mode), ensure_ascii=False, allow_nan=False
                )
            )
        finally:
            node.close()
    else:
        node = RPCClient(args.rpc, os.environ["RETRIEVALLAB_WORKER_TOKEN"])
        try:
            print(json.dumps(Worker(registry, store, principal, args.engine, node).run_once()))
        finally:
            node.close()
    return 0
