"""Measure a pinned local workload; report observations without CI thresholds."""

import argparse
import concurrent.futures
import platform
import statistics
import time
from pathlib import Path

from retrievallab.client.http import Client
from retrievallab.corpus.snapshot import canonical


def measure(client: Client, count: int, concurrency: int) -> dict:
    stats = client.stats()
    def request(_: int) -> tuple[float, float]:
        start = time.perf_counter()
        response = client.search("retrieval")
        if response["snapshot_id"] != stats["snapshot_id"]:
            raise ValueError("snapshot changed during benchmark")
        return (time.perf_counter() - start) * 1000, response["timings"]["search_ms"]
    for i in range(5):
        request(i)
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        pairs = list(executor.map(request, range(count)))
    def percentiles(values: list[float]) -> dict:
        values.sort()
        return {"p50_ms": statistics.median(values), "p95_ms": values[max(0, (95 * len(values) + 99) // 100 - 1)]}
    return {"schema_version": 1, "service": stats, "warmups": 5, "request_count": count, "concurrency": concurrency, "query": "retrieval", "condition": "warm", "round_trip": percentiles([p[0] for p in pairs]), "server": percentiles([p[1] for p in pairs]), "environment": {"os": platform.platform(), "cpu": platform.processor(), "python": platform.python_version()}, "peak_memory": None, "memory_note": "Not measured by this transport-only harness."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8091")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--count", default=100, type=int)
    parser.add_argument("--concurrency", default=1, type=int)
    args = parser.parse_args()
    if not 1 <= args.count <= 10000 or not 1 <= args.concurrency <= 16:
        parser.error("invalid workload bounds")
    result = measure(Client(args.url), args.count, args.concurrency)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(result) + b"\n")
