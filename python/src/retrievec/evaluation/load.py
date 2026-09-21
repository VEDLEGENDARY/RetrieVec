"""Bounded authenticated workspace workloads with complete failure accounting."""

import asyncio
import hashlib
import json
import math
import os
import platform
import re
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from retrievec.telemetry import CONTEXT, correlate

PROFILES = {
    "single-researcher": {"concurrency": 1, "requests": 10, "workflow": "research"},
    "concurrent-search": {"concurrency": 4, "requests": 40, "workflow": "search"},
    "mixed-ingestion-search": {"concurrency": 2, "requests": 12, "workflow": "mixed"},
    "slow-provider": {"concurrency": 2, "requests": 8, "workflow": "research"},
}


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    left, right = math.floor(position), math.ceil(position)
    return ordered[left] + (ordered[right] - ordered[left]) * (position - left)


def summarize(records):
    durations = [row["elapsed_ms"] for row in records]
    successful = [row["elapsed_ms"] for row in records if row["outcome"] == "completed"]
    errors = {}
    for row in records:
        if row["outcome"] != "completed":
            errors[row["error_code"]] = errors.get(row["error_code"], 0) + 1
    return {
        "request_count": len(records),
        "successes": len(successful),
        "failures": len(records) - len(successful),
        "errors": errors,
        "all_outcomes_ms": {"p50": percentile(durations, 0.5), "p95": percentile(durations, 0.95)},
        "successful_ms": {"p50": percentile(successful, 0.5), "p95": percentile(successful, 0.95)},
    }


class WorkloadFailure(Exception):
    def __init__(self, code):
        self.code = code


def append_record(path, row):
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
        file.flush()
        os.fsync(file.fileno())


async def execute(args, *, transport=None):
    address = urlsplit(args.origin)
    if (
        address.scheme != "http"
        or address.hostname not in ("127.0.0.1", "::1", "localhost")
        or address.username
        or address.password
        or address.path not in ("", "/")
        or address.query
        or address.fragment
    ):
        raise ValueError("load execution is restricted to a loopback workspace origin")
    profile = PROFILES[args.profile]
    concurrency = profile["concurrency"] if args.concurrency is None else args.concurrency
    count = profile["requests"] if args.requests is None else args.requests
    if not 1 <= concurrency <= 8 or not 1 <= count <= 500 or not 0 <= args.warmup <= 20:
        raise ValueError("workload limits exceeded")
    if not 1 <= args.timeout <= 360 or not 1 <= args.wall_seconds <= 3600:
        raise ValueError("invalid time budget")
    if args.corpus_size is not None and args.corpus_size < 0:
        raise ValueError("corpus size must be nonnegative")
    if profile["workflow"] != "search" and not args.allow_mutations:
        raise ValueError("this profile creates saved runs or collections; pass --allow-mutations")
    if args.profile == "slow-provider" and not args.slow_provider_confirmed:
        raise ValueError("configure a deliberately slow local provider and acknowledge it")
    session_path = Path(args.session)
    if session_path.stat().st_size > 16384:
        raise ValueError("session file too large")
    session = json.loads(session_path.read_text(encoding="utf-8"))
    if Path(args.queries).stat().st_size > 4 * 1024 * 1024:
        raise ValueError("question file too large")
    dataset = Path(args.queries).read_bytes()
    questions = json.loads(dataset)
    if not isinstance(questions, list) or not questions or len(questions) > 1000:
        raise ValueError("expected a bounded JSON list of questions")
    if any(not isinstance(q, str) or not 1 <= len(q.strip()) <= 4096 for q in questions):
        raise ValueError("invalid question")
    # Never persist cookies, question text, response bodies, or CSRF tokens in the load record.
    headers = {"Origin": args.origin.rstrip("/"), "X-CSRF-Token": session["csrf_token"]}
    cookies = {"retrievec_session": session["session_cookie"]}
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    start = time.monotonic()
    records, warmup = [], []
    destination = Path(args.output)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "execution.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "profile": args.profile,
                "planned_requests": count,
                "planned_warmup": args.warmup,
                "concurrency": concurrency,
                "query_sha256": hashlib.sha256(dataset).hexdigest(),
                "completion_record": "report.json",
                "incomplete_without_report": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    async with httpx.AsyncClient(
        base_url=args.origin.rstrip("/"),
        headers=headers,
        cookies=cookies,
        trust_env=False,
        follow_redirects=False,
        limits=limits,
        timeout=httpx.Timeout(15, connect=3),
        transport=transport,
    ) as client:

        async def request(method, path, **kwargs):
            headers = dict(kwargs.pop("headers", {}))
            headers["X-Request-ID"] = CONTEXT.get().get("request_id", uuid.uuid4().hex)
            kwargs["headers"] = headers
            result = await client.request(method, path, **kwargs)
            if not result.is_success:
                raise WorkloadFailure("http_" + str(result.status_code))
            return result.json() if result.content else None

        async def terminal(path, success):
            while True:
                value = await request("GET", path)
                if value["state"] == success:
                    return value
                if value["state"] in ("failed", "cancelled"):
                    raise WorkloadFailure("terminal_" + value["state"])
                await asyncio.sleep(0.5)

        async def operation(index, row):
            question = questions[index % len(questions)]
            row["query_hash"] = hashlib.sha256(question.encode()).hexdigest()
            collection = args.collection
            conversation = None
            if profile["workflow"] == "mixed" and index % 2 == 0:
                created = await request(
                    "POST", "/api/v1/collections", json={"title": "Synthetic load rehearsal"}
                )
                collection = created["collection_id"]
                row["created_collection_id"] = collection
                append_record(destination / "progress.jsonl", {**row, "outcome": "in_progress"})
                stage_start = time.perf_counter()
                job = await request(
                    "POST",
                    f"/api/v1/collections/{collection}/uploads",
                    files={
                        "files": (
                            "load-fixture.txt",
                            b"Synthetic retrieval evidence. Dense and lexical methods "
                            b"retrieve passages.",
                            "text/plain",
                        )
                    },
                    headers={"Idempotency-Key": row["request_id"]},
                )
                row["job_id"] = job["job_id"]
                append_record(destination / "progress.jsonl", {**row, "outcome": "in_progress"})
                await terminal(f"/api/v1/jobs/{job['job_id']}", "succeeded")
                row["ingestion_wall_ms"] = (time.perf_counter() - stage_start) * 1000
            stage_start = time.perf_counter()
            search = await request(
                "POST",
                "/api/v1/search",
                json={"collection_id": collection, "query": question, "retrieval": "compare"},
            )
            row["search_wall_ms"] = (time.perf_counter() - stage_start) * 1000
            row["snapshot_id"] = search["snapshot_id"]
            row["search_server_timings"] = {
                mode: result.get("timings", {}) for mode, result in search["results"].items()
            }
            if profile["workflow"] in ("research", "mixed"):
                conversation = await request(
                    "POST",
                    "/api/v1/conversations",
                    json={"collection_id": collection, "title": "Synthetic load run"},
                )
                run = await request(
                    "POST",
                    f"/api/v1/conversations/{conversation['conversation_id']}/runs",
                    json={"question": question, "provider": args.provider},
                    headers={"Idempotency-Key": row["request_id"]},
                )
                row["run_id"] = run["run_id"]
                append_record(destination / "progress.jsonl", {**row, "outcome": "in_progress"})
                stage_start = time.perf_counter()
                finished = await terminal(f"/api/v1/runs/{run['run_id']}", "completed")
                row["research_wall_ms"] = (time.perf_counter() - stage_start) * 1000
                row["research_server_ms"] = finished["result"]["elapsed_ms"]
                exported = await request(
                    "POST", f"/api/v1/runs/{run['run_id']}/exports", json={"format": "json"}
                )
                if not re.fullmatch(r"/api/v1/exports/[0-9a-f-]{36}", exported["download_url"]):
                    raise WorkloadFailure("invalid_export_url")
                response = await client.get(
                    exported["download_url"], headers={"X-Request-ID": row["request_id"]}
                )
                if response.status_code != 200:
                    raise WorkloadFailure("export_" + str(response.status_code))

        async def measure(index, is_warmup=False):
            row = {
                "index": index,
                "request_id": uuid.uuid4().hex,
                "outcome": "completed",
                "error_code": None,
                "warmup": is_warmup,
            }
            elapsed = time.perf_counter()
            append_record(
                destination / "started.jsonl",
                {"index": index, "request_id": row["request_id"], "warmup": is_warmup},
            )
            remaining = args.wall_seconds - (time.monotonic() - start)
            try:
                if remaining <= 0:
                    raise WorkloadFailure("wall_budget_exhausted")
                with correlate(request_id=row["request_id"]):
                    await asyncio.wait_for(
                        operation(index, row), timeout=min(args.timeout, remaining)
                    )
            except (TimeoutError, httpx.TimeoutException):
                row.update(outcome="failed", error_code="timeout")
            except httpx.HTTPError:
                row.update(outcome="failed", error_code="transport")
            except WorkloadFailure as error:
                row.update(outcome="failed", error_code=error.code)
            except (ValueError, KeyError, TypeError):
                row.update(outcome="failed", error_code="invalid_response")
            except asyncio.CancelledError:
                row.update(outcome="failed", error_code="interrupted")
                raise
            except Exception:
                row.update(outcome="failed", error_code="runner_error")
                raise
            finally:
                row["elapsed_ms"] = round((time.perf_counter() - elapsed) * 1000, 3)
                # Request cancellation after timeout; preserve IDs if recovery is necessary.
                try:
                    if row["outcome"] == "failed" and row.get("run_id"):
                        try:
                            with correlate(request_id=row["request_id"]):
                                await asyncio.wait_for(
                                    request("POST", f"/api/v1/runs/{row['run_id']}/cancel"),
                                    timeout=5,
                                )
                        except (Exception, asyncio.CancelledError):
                            row["cleanup_pending"] = True
                finally:
                    (warmup if is_warmup else records).append(row)
                    append_record(
                        destination / ("warmup.jsonl" if is_warmup else "requests.jsonl"), row
                    )
            return row

        for index in range(args.warmup):
            await measure(index, True)
        queue = asyncio.Queue()
        for index in range(count):
            queue.put_nowait(index)

        async def consume():
            while True:
                try:
                    index = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                await measure(index)

        async with asyncio.TaskGroup() as tasks:
            for _ in range(concurrency):
                tasks.create_task(consume())
    report = {
        "schema_version": 1,
        "profile": args.profile,
        "concurrency": concurrency,
        "warmup": {"count": len(warmup), "summary": summarize(warmup)},
        "results": summarize(records),
        "query_sha256": hashlib.sha256(dataset).hexdigest(),
        "elapsed_seconds": time.monotonic() - start,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "server_cpu_ram": None,
        "corpus_size": args.corpus_size,
        "configuration_note": args.configuration_note,
        "timing_policy": "wall includes transport/queue/model; server stages are separate",
        "note": "Server CPU/RAM requires explicitly selected PIDs; inspect sampling errors.",
    }
    (destination / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
