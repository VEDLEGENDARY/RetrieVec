"""Capture three modes on one pinned snapshot and propose an unreviewed pool."""

import argparse
import os
from pathlib import Path

from retrievec.client.capture import capture
from retrievec.client.rpc import RPCClient
from retrievec.corpus.snapshot import canonical, parse_json
from retrievec.dense.hybrid import PinnedClient
from retrievec.dense.model import adapter
from retrievec.registry.artifacts import Store
from retrievec.registry.database import Registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--embedding", choices=("fixture", "minilm"), default="minilm")
    parser.add_argument("--rpc", default="127.0.0.1:8092")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    registry, store = Registry(os.environ["RETRIEVEC_DSN"]), Store(args.store)
    principal = os.environ["RETRIEVEC_PRINCIPAL"]
    snapshot_id = registry.resolve(principal, args.collection)["snapshot_id"]
    node = RPCClient(args.rpc, os.environ["RETRIEVEC_READ_TOKEN"])
    try:
        model = adapter(args.embedding)
        pool = {}
        summaries = {}
        for mode in ("sparse", "dense", "hybrid"):
            client = PinnedClient(
                registry, store, node, principal, args.collection, mode, model, snapshot_id
            )
            summaries[mode] = capture(client, args.queries, args.output / mode)
            for line in (args.output / mode / "results.jsonl").read_bytes().splitlines():
                result = parse_json(line)
                for hit in result.get("response", {}).get("hits", []):
                    key = (result["query_id"], hit["chunk_id"])
                    pool.setdefault(key, set()).add(mode)
        rows = [
            {
                "query_id": query,
                "chunk_id": chunk,
                "retrievers": sorted(modes),
                "grade": None,
                "reviewer": None,
                "review_status": "draft",
            }
            for (query, chunk), modes in sorted(pool.items())
        ]
        (args.output / "review-pool.jsonl").write_bytes(
            b"".join(canonical(row) + b"\n" for row in rows)
        )
        (args.output / "comparison.json").write_bytes(
            canonical(
                {
                    "snapshot_id": snapshot_id,
                    "modes": summaries,
                    "reviewed_quality_available": False,
                }
            )
            + b"\n"
        )
    finally:
        node.close()


if __name__ == "__main__":
    main()
