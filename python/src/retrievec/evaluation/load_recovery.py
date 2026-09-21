"""Summarize durable workload journals without retrying uncertain requests."""

import json
import math
import re
from pathlib import Path

from retrievec.evaluation.load import summarize


def read_journal(path):
    if not path.exists():
        return [], False
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("workload journal exceeds bound")
    raw = path.read_bytes()
    lines, records = raw.splitlines(), []
    truncated = False
    for number, line in enumerate(lines):
        try:
            row = json.loads(line)
        except ValueError:
            if number == len(lines) - 1 and not raw.endswith(b"\n"):
                truncated = True
                continue
            raise ValueError("invalid workload journal") from None
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("request_id"), str)
            or not re.fullmatch(r"[0-9a-f]{32}", row["request_id"])
            or type(row.get("warmup")) is not bool
            or type(row.get("index")) is not int
        ):
            raise ValueError("invalid workload identity")
        records.append(row)
    return records, truncated


def recover(directory):
    root = Path(directory)
    execution = json.loads((root / "execution.json").read_bytes())
    if execution.get("schema_version") != 1:
        raise ValueError("unsupported workload execution")
    starts, tail_a = read_journal(root / "started.jsonl")
    measured, tail_b = read_journal(root / "requests.jsonl")
    warmup, tail_c = read_journal(root / "warmup.jsonl")
    progress, tail_d = read_journal(root / "progress.jsonl")
    started = {row["request_id"]: row for row in starts}
    if len(started) != len(starts):
        raise ValueError("duplicate workload start")
    outcomes = {}
    for row in [*measured, *warmup]:
        key = row["request_id"]
        if key in outcomes or key not in started:
            raise ValueError("duplicate or unstarted outcome")
        if any(row[field] != started[key][field] for field in ("index", "warmup")):
            raise ValueError("outcome identity differs from start")
        elapsed = row.get("elapsed_ms")
        if (
            row.get("outcome") not in ("completed", "failed")
            or type(elapsed) not in (int, float)
            or not math.isfinite(elapsed)
            or elapsed < 0
        ):
            raise ValueError("invalid workload outcome")
        if row["outcome"] == "failed" and not isinstance(row.get("error_code"), str):
            raise ValueError("failed workload lacks error code")
        outcomes[key] = row
    for row in progress:
        if row["request_id"] not in started:
            raise ValueError("unstarted workload progress")
        if any(row[field] != started[row["request_id"]][field] for field in ("index", "warmup")):
            raise ValueError("progress identity differs from start")
        started[row["request_id"]].update(row)
    results = {}
    for name, flag, planned in (
        ("measured", False, execution["planned_requests"]),
        ("warmup", True, execution["planned_warmup"]),
    ):
        if type(planned) is not int or not 0 <= planned <= 500:
            raise ValueError("invalid planned count")
        group = [row for row in started.values() if row["warmup"] == flag]
        indices = [row["index"] for row in group]
        if len(set(indices)) != len(indices) or any(not 0 <= index < planned for index in indices):
            raise ValueError("invalid planned index")
        completed = [row for row in outcomes.values() if row["warmup"] == flag]
        unknown = [
            {
                key: row[key]
                for key in ("request_id", "index", "run_id", "job_id", "created_collection_id")
                if key in row
            }
            for row in group
            if row["request_id"] not in outcomes
        ]
        results[name] = {
            "planned": planned,
            "never_started": planned - len(group),
            "unknown_outcomes": unknown,
            "recorded": summarize(completed),
        }
    return {
        "schema_version": 1,
        "completion_report_present": (root / "report.json").is_file(),
        "truncated_journal": any((tail_a, tail_b, tail_c, tail_d)),
        **results,
        "policy": "Unknown outcomes are not successes or timed failures. Inspect retained "
        "resource IDs before retrying; no requests are reissued by recovery.",
    }
