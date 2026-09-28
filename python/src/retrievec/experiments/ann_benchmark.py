"""ANN recall, judged relevance and resource reporting remain separate."""

from __future__ import annotations

import os
import statistics
import time
from pathlib import Path

import numpy as np

from retrievec.evaluation.metrics import aggregate, metrics
from retrievec.experiments.ann import IVFConfig, IVFIndex, timed_search


def benchmark_ann(
    vectors: np.ndarray,
    chunk_ids: list[str],
    queries: list[dict],
    judgments: dict[str, dict[str, int]],
    snapshot_id: str,
    config: IVFConfig,
    *,
    top_k: int = 10,
    serialized_path: Path | None = None,
) -> dict:
    build_started = time.perf_counter()
    index = IVFIndex(vectors, chunk_ids, snapshot_id, config)
    build_ms = (time.perf_counter() - build_started) * 1000
    recalls, latencies, relevance, failures = [], [], [], []
    for query in queries:
        try:
            vector = np.asarray(query["vector"], dtype=np.float32)
            exact = index.exact(vector, top_k=top_k)
            approximate, elapsed = timed_search(index, vector, top_k=top_k, snapshot_id=snapshot_id)
            exact_ids = {row["chunk_id"] for row in exact}
            approximate_ids = [row["chunk_id"] for row in approximate]
            recalls.append(
                len(exact_ids.intersection(approximate_ids)) / len(exact_ids) if exact_ids else 1.0
            )
            latencies.append(elapsed)
            relevance.append(metrics(approximate_ids, judgments.get(query["query_id"], {}), top_k))
        except Exception as error:
            failures.append({"query_id": query.get("query_id"), "error": type(error).__name__})
    ordered = sorted(latencies)

    def percentile(q):
        return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * q))] if ordered else None

    return {
        "schema_version": 1,
        "index_id": index.index_id,
        "snapshot_id": snapshot_id,
        "configuration": config.__dict__,
        "scale": {"vectors": len(chunk_ids), "dimension": int(vectors.shape[1])},
        "build_ms": build_ms,
        "memory_bytes": int(index.centers.nbytes + sum(group.nbytes for group in index.members)),
        "disk_bytes": os.path.getsize(serialized_path)
        if serialized_path and serialized_path.exists()
        else None,
        "ann_recall_at_k": {
            "mean": statistics.fmean(recalls) if recalls else None,
            "queries": len(recalls),
        },
        "judged_relevance": aggregate(relevance),
        "latency_ms": {"p50": percentile(0.5), "p95": percentile(0.95), "samples": len(latencies)},
        "failures": failures,
        "distance_counts": None,
        "distance_counts_reason": "numpy backend does not expose distance-operation counters",
    }
