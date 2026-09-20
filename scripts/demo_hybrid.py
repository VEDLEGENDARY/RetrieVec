"""Exercise durable ingestion and three-mode retrieval against local PostgreSQL."""

import argparse
import os
import queue
import subprocess
import threading
import uuid
from pathlib import Path

from retrievallab.client.capture import capture
from retrievallab.client.rpc import RPCClient
from retrievallab.corpus.snapshot import canonical, digest, parse_json
from retrievallab.dense.hybrid import PinnedClient
from retrievallab.dense.model import adapter
from retrievallab.registry.artifacts import Store
from retrievallab.registry.database import Registry
from retrievallab.registry.jobs import Jobs
from retrievallab.registry.worker import Worker, stage_inputs

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--embedding", choices=("fixture", "minilm"), default="fixture")
    parser.add_argument(
        "--engine",
        type=Path,
        default=ROOT / "artifacts/bin" / ("retrievald.exe" if os.name == "nt" else "retrievald"),
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    args.output.mkdir(parents=True)
    registry = Registry(os.environ["RETRIEVALLAB_DSN"])
    registry.migrate()
    principal, collection = "demo-" + uuid.uuid4().hex, "demo-" + uuid.uuid4().hex
    registry.create_collection(principal, collection)
    store = Store(args.output / "store")
    source_root = args.output / "sources"
    source_root.mkdir()
    sources = []
    for item in parse_json((ROOT / "datasets/fixtures/synthetic_sources.json").read_bytes()):
        raw = item["text"].encode()
        name = item["paper_id"] + ".txt"
        (source_root / name).write_bytes(raw)
        sources.append(
            {
                "paper_id": item["paper_id"],
                "title": item["title"],
                "authors": [],
                "path": name,
                "source_url": None,
                "source_sha256": digest(raw),
                "license_note": "Original synthetic fixture",
            }
        )
    manifest_path = args.output / "sources.json"
    manifest_path.write_bytes(canonical({"schema_version": 1, "sources": sources}))
    payload = stage_inputs(store, manifest_path, source_root)
    job = Jobs(registry, principal).enqueue(
        collection, "demo-v1", payload, {"token_budget": 96, "embedding": args.embedding}
    )
    read_token, worker_token = uuid.uuid4().hex, uuid.uuid4().hex
    environment = {
        **os.environ,
        "RETRIEVALLAB_PRINCIPAL": principal,
        "RETRIEVALLAB_READ_TOKEN": read_token,
        "RETRIEVALLAB_WORKER_TOKEN": worker_token,
    }

    def start():
        process = subprocess.Popen(
            [
                str(args.engine.resolve()),
                "rpc",
                "--store",
                str(store.root),
                "--listen",
                "127.0.0.1:0",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        lines = queue.Queue()
        threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
        try:
            line = lines.get(timeout=25).strip()
            if not line.startswith("listening grpc://"):
                raise RuntimeError("RPC startup failed")
            address = line.removeprefix("listening grpc://")
            return process, RPCClient(address, read_token), RPCClient(address, worker_token)
        except BaseException:
            process.terminate()
            process.communicate(timeout=10)
            raise

    process, reader, worker = start()
    model = adapter(args.embedding)
    records = {}
    try:
        outcome = Worker(registry, store, principal, args.engine, worker).run_once()
        if outcome is None or outcome["state"] != "succeeded":
            raise RuntimeError(f"ingestion failed: {outcome}")
        query_file = args.output / "queries.jsonl"
        query_file.write_bytes(
            b"".join(
                canonical({"query_id": f"q{i}", "query": query, "mode": "free_text", "top_k": 10})
                + b"\n"
                for i, query in enumerate(
                    ("retrieval", "semantic vocabulary mismatch", "rank fusion", "source hashes")
                )
            )
        )
        for mode in ("sparse", "dense", "hybrid"):
            client = PinnedClient(registry, store, reader, principal, collection, mode, model)
            records[mode] = capture(client, query_file, args.output / mode)
        pinned_id = outcome["snapshot_id"]
    finally:
        reader.close()
        worker.close()
        process.terminate()
        process.communicate(timeout=10)
    process, reader, worker = start()
    try:
        client = PinnedClient(
            registry, store, reader, principal, collection, "hybrid", model, pinned_id
        )
        repeated = capture(client, query_file, args.output / "hybrid-restart")
        if repeated["ranking_sha256"] != records["hybrid"]["ranking_sha256"]:
            raise RuntimeError("restart changed ranking")
        evidence = {
            "schema_version": 1,
            "collection": collection,
            "job_id": str(job["job_id"]),
            "snapshot_id": pinned_id,
            "model_configuration": model.config,
            "runs": records,
            "restart_rankings_equal": True,
            "reviewed_quality_available": False,
        }
        (args.output / "evidence.json").write_bytes(canonical(evidence) + b"\n")
        print(args.output / "evidence.json")
    finally:
        reader.close()
        worker.close()
        process.terminate()
        process.communicate(timeout=10)


if __name__ == "__main__":
    main()
