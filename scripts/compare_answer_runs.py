"""Re-score two saved provider runs without inventing human faithfulness labels."""

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from retrievec.evaluation.answer_signals import automatic_signals


def compare(paths: list[Path]) -> dict:
    if len(paths) < 2:
        raise ValueError("at least two saved model runs are required")
    runs, reference = [], None
    for path in paths:
        raw = path.read_bytes()
        report = json.loads(raw)
        if report.get("schema_version") != 1 or not isinstance(report.get("results"), list):
            raise ValueError("unsupported generation report")
        cases = {(row["id"], row["question"]) for row in report["results"]}
        if len(cases) != len(report["results"]) or (reference is not None and cases != reference):
            raise ValueError("model runs must contain identical question IDs and text")
        reference = cases
        rescored = []
        for row in report["results"]:
            signals = automatic_signals(
                row.get("raw_output", ""),
                row.get("evidence", []),
                expected_unanswerable=row.get("empty"),
            )
            rescored.append(
                {
                    "question_id": row["id"],
                    "question": row["question"],
                    "raw_output": row.get("raw_output"),
                    "evidence_ids": [item["evidence_id"] for item in row.get("evidence", [])],
                    "automatic": signals,
                    "elapsed_ms": row.get("elapsed_ms"),
                }
            )
        timing = sorted(row["elapsed_ms"] for row in rescored if row["elapsed_ms"] is not None)
        runs.append(
            {
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "provider": report["provider"],
                "case_count": len(rescored),
                "evidence_sha256_by_case": {
                    row["id"]: hashlib.sha256(
                        json.dumps(row.get("evidence", []), sort_keys=True).encode()
                    ).hexdigest()
                    for row in report["results"]
                },
                "structurally_valid_count": sum(
                    row["automatic"]["structurally_valid"] for row in rescored
                ),
                "latency_ms": {
                    "median": statistics.median(timing) if timing else None,
                    "p95": timing[min(len(timing) - 1, int((len(timing) - 1) * 0.95))]
                    if timing
                    else None,
                },
                "cases": rescored,
            }
        )
    prompt_versions = {run["provider"].get("prompt_version") for run in runs}
    evidence_identical = all(
        run["evidence_sha256_by_case"] == runs[0]["evidence_sha256_by_case"] for run in runs[1:]
    )
    return {
        "schema_version": 1,
        "kind": "retrospective-automatic-model-comparison",
        "case_count": len(reference),
        "evidence_kind": "synthetic",
        "prompt_versions_equal": len(prompt_versions) == 1,
        "evidence_identical": evidence_identical,
        "controlled_quality_comparison": False,
        "human_review_count": 0,
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.run)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
