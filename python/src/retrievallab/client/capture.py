"""Capture exact requests, results and provenance without assigning quality metrics."""

import hashlib
import os
import platform
import shutil
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import grpc

from retrievallab import __version__
from retrievallab.client.http import Client, RetrievalError
from retrievallab.corpus.snapshot import canonical, parse_json


def git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], stderr=subprocess.DEVNULL, text=True, timeout=5
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def capture(client: Client, query_file: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("output directory already exists")
    if query_file.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("query file exceeds 4 MiB")
    raw = query_file.read_bytes()
    requests = []
    ids = set()
    for line in raw.splitlines():
        record = parse_json(line)
        if (
            not isinstance(record, dict)
            or not {"query_id", "query"} <= record.keys()
            or record.keys() - {"query_id", "query", "mode", "top_k", "explain"}
        ):
            raise ValueError("invalid query record fields")
        if (
            not isinstance(record["query_id"], str)
            or not record["query_id"]
            or record["query_id"] in ids
            or not isinstance(record["query"], str)
        ):
            raise ValueError("invalid or duplicate query identity")
        ids.add(record["query_id"])
        requests.append(record)
    if not requests or len(requests) > 1000:
        raise ValueError("query file requires 1–1000 records")
    stats = client.stats()
    results = []
    stable = []
    for record in requests:
        started = time.perf_counter()
        row = {
            "query_id": record["query_id"],
            "request": {
                "query": record["query"],
                "mode": record.get("mode", "free_text"),
                "top_k": record.get("top_k", 10),
                "explain": record.get("explain", False),
            },
        }
        try:
            response = client.search(**row["request"])
            for key in (
                "snapshot_id",
                "collection_id",
                "analyzer_version",
                "scoring_version",
                "configuration",
            ):
                if response[key] != stats[key]:
                    raise RetrievalError(
                        "snapshot_changed", "service identity/configuration changed during run"
                    )
            row["response"] = response
        except RetrievalError as error:
            row["error"] = {"code": error.code, "message": str(error), "status": error.status}
        except (ValueError, grpc.RpcError) as error:
            row["error"] = {
                "code": error.code().name if isinstance(error, grpc.RpcError) else "invalid_input",
                "message": "retrieval request failed",
                "status": None,
            }
        row["round_trip_ms"] = (time.perf_counter() - started) * 1000
        results.append(row)
        stable.append(
            {
                "query_id": row["query_id"],
                "request": row["request"],
                "hits": row.get("response", {}).get("hits"),
                "error": row.get("error"),
            }
        )
    result_bytes = b"".join(canonical(row) + b"\n" for row in results)
    dirty = git_value("status", "--porcelain")
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "client_version": __version__,
        "service_url": client.base_url,
        "service": stats,
        "query_sha256": hashlib.sha256(raw).hexdigest(),
        "results_sha256": hashlib.sha256(result_bytes).hexdigest(),
        "ranking_sha256": hashlib.sha256(canonical(stable)).hexdigest(),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_dirty": None if dirty is None else bool(dirty),
        "environment": {
            "python": platform.python_version(),
            "os": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
        },
        "warmups": 0,
        "request_count": len(results),
        "concurrency": 1,
        "error_count": sum("error" in row for row in results),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".run-", dir=output.parent))
    try:
        (staging / "results.jsonl").write_bytes(result_bytes)
        (staging / "manifest.json").write_bytes(canonical(manifest) + b"\n")
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return manifest
