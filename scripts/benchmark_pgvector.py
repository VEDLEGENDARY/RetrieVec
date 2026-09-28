"""Compare optional pgvector exact/HNSW against pinned exhaustive cosine vectors."""

import argparse
import json
import math
import os
import time
from pathlib import Path

import psycopg
from retrievec.corpus.snapshot import canonical, digest
from retrievec.dense.artifacts import load_embeddings
from retrievec.dense.search import exact_search
from retrievec.evaluation.metrics import aggregate, metrics
from retrievec.experiments.pgvector import PgvectorIndex, VectorConfig, build, initialize
from retrievec.registry.artifacts import Store
from retrievec.registry.database import Registry


def timings(values):
    ordered = sorted(values)
    return {
        "samples": len(values),
        **{
            label: ordered[max(0, math.ceil(len(ordered) * fraction) - 1)] if ordered else None
            for label, fraction in (("p50", 0.5), ("p95", 0.95))
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--ef-search", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.top_k <= 1000:
        parser.error("top-k must be between 1 and 1000")
    registry = Registry(os.environ["RETRIEVEC_DSN"])
    store = Store(args.store)
    registered = registry.resolve(args.principal, args.collection, args.snapshot)
    manifest = registered["manifest"]
    embedding, vectors = load_embeddings(
        store, manifest["embedding_id"], manifest["corpus_snapshot_id"]
    )
    bundle = json.loads(args.queries.read_text(encoding="utf-8"))
    queries = bundle["queries"]
    if bundle["configuration"] != embedding["configuration"] or not 1 <= len(queries) <= 10000:
        raise ValueError("bounded query set with matching encoder configuration required")
    ids = [row["query_id"] for row in queries]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate query IDs")
    if args.initialize:
        initialize(registry)
    started = time.perf_counter()
    config = VectorConfig(ef_search=args.ef_search)
    index_id = build(registry, store, args.principal, args.collection, args.snapshot, config)
    build_ms = (time.perf_counter() - started) * 1000
    index = PgvectorIndex(registry, args.principal, args.collection, args.snapshot, index_id)
    latencies = {key: [] for key in ("reference", "exact", "hnsw")}
    relevance = {key: [] for key in latencies}
    recalls, parity, failures = [], [], []
    chunk_ids = [row["chunk_id"] for row in embedding["chunks"]]
    for query in queries:
        try:
            rankings = {}
            for backend in latencies:
                begin = time.perf_counter()
                ranking = (
                    exact_search(vectors, chunk_ids, query["vector"], args.top_k)
                    if backend == "reference"
                    else index.search(
                        query["vector"],
                        configuration=bundle["configuration"],
                        top_k=args.top_k,
                        approximate=backend == "hnsw",
                    )
                )
                latencies[backend].append((time.perf_counter() - begin) * 1000)
                rankings[backend] = [row["chunk_id"] for row in ranking]
                if "judgments" in query:
                    relevance[backend].append(
                        metrics(rankings[backend], query["judgments"], args.top_k)
                    )
            reference = set(rankings["reference"])
            recalls.append(
                len(reference & set(rankings["hnsw"])) / len(reference) if reference else 1
            )
            parity.append(rankings["reference"] == rankings["exact"])
        except (ValueError, PermissionError, psycopg.Error) as error:
            failures.append({"query_id": query["query_id"], "error": type(error).__name__})
    with registry.connect() as db:
        registry.authorize(db, args.principal, args.collection, read=True)
        resource = db.execute(
            "SELECT pg_total_relation_size(%s::regclass) AS disk_bytes",
            ("retrievec_experiments.v_" + index_id[3:51],),
        ).fetchone()
    report = {
        "schema_version": 1,
        "index_id": index_id,
        "snapshot_id": args.snapshot,
        "embedding_id": manifest["embedding_id"],
        "query_bundle_sha256": digest(canonical(bundle)),
        "configuration": bundle["configuration"],
        "index_configuration": config.__dict__,
        "scale": {
            "vectors": len(vectors),
            "dimension": embedding["dimension"],
            "queries": len(queries),
        },
        "build_or_verify_ms": build_ms,
        "resources": {**resource, "peak_memory_bytes": None},
        "latency_ms": {key: timings(values) for key, values in latencies.items()},
        "ann_recall_at_k": sum(recalls) / len(recalls) if recalls else None,
        "exact_ranking_parity": bool(parity) and all(parity),
        "judged_relevance": {key: aggregate(values) for key, values in relevance.items()},
        "judgment_provenance": bundle.get("judgment_provenance", "unreviewed"),
        "failures": failures,
        "decision": "retain_reference_pending_review",
        "limitations": [
            "No automatic default change",
            "Process memory not measured",
            "Fixed backend order; rerun with controlled cache/warmup conditions",
            "Fixture vectors and unreviewed judgments do not establish quality",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(report) + b"\n")


if __name__ == "__main__":
    main()
