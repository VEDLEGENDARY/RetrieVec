"""Run pinned generation providers on passage-linked questions and export blank reviews."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import statistics
import time
from pathlib import Path

import httpx
from retrievec.app.answers import abstention, answer_schema
from retrievec.app.generation import LlamaProvider, load_providers, pack_evidence
from retrievec.evaluation.answer_signals import automatic_signals
from retrievec.evaluation.files import validate_outputs, write_json
from retrievec.evaluation.nli_proxy import NliConfig, NliProxy


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_cases(path: Path) -> tuple[dict, list[tuple[dict, list[dict]]]]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(dataset, dict)
        or dataset.get("schema_version") != 1
        or not isinstance(dataset.get("questions"), list)
        or not dataset["questions"]
    ):
        raise ValueError("expected versioned questions dataset")
    global_evidence = dataset.get("evidence", [])
    cases = []
    seen = set()
    for item in dataset["questions"]:
        if not isinstance(item, dict):
            raise ValueError("each question must be an object")
        if any(
            field in item and type(item[field]) is not bool for field in ("empty", "unanswerable")
        ):
            raise ValueError("question flags must be booleans")
        case_id, question = item.get("id"), item.get("question")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError("question IDs must be unique nonempty strings")
        seen.add(case_id)
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"question {case_id} has no text")
        if "effective_query" in item and (
            not isinstance(item["effective_query"], str) or not item["effective_query"].strip()
        ):
            raise ValueError(f"question {case_id} has invalid effective query")
        evidence = [] if item.get("empty") else item.get("evidence", global_evidence)
        if not isinstance(evidence, list) or any(
            not isinstance(row, dict)
            or not isinstance(row.get("chunk_id"), str)
            or not row["chunk_id"].strip()
            or not isinstance(row.get("text"), str)
            or not row["text"].strip()
            for row in evidence
        ):
            raise ValueError(f"question {case_id} has invalid evidence")
        if len({row["chunk_id"] for row in evidence}) != len(evidence):
            raise ValueError(f"question {case_id} has duplicate evidence")
        cases.append((item, evidence))
    return dataset, cases


async def run_case(provider: LlamaProvider, case: dict, evidence: list[dict], nli=None) -> dict:
    started = time.perf_counter()
    row = {"question_id": case["id"], "failure": None}
    try:
        query = case.get("effective_query", case["question"])
        packet = await pack_evidence(provider, query, evidence)
        # Save exactly what was packed, including evidence IDs, before generation can fail.
        row["evidence"] = packet["evidence"]
        row["effective_query"] = query
        row["evidence_ids"] = [item["evidence_id"] for item in packet["evidence"]]
        row["input_tokens"] = packet["input_tokens"]
        row["excluded"] = packet["excluded"]
        raw = (
            await provider.generate(packet["prompt"], answer_schema(packet["evidence"]))
            if packet["evidence"]
            else json.dumps(abstention())
        )
        row["answer"] = raw
        row["automatic"] = automatic_signals(
            raw,
            packet["evidence"],
            expected_unanswerable=case.get("unanswerable", True if case.get("empty") else None),
            entailment=nli,
        )
    except (ValueError, OSError, TimeoutError, RuntimeError, httpx.HTTPError) as error:
        row["failure"] = type(error).__name__ + ": " + str(error)[:240]
    row["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return row


async def evaluate(args: argparse.Namespace) -> dict:
    dataset, cases = load_cases(args.dataset)
    providers = load_providers(args.providers)
    if len(args.model) < 2 or len(set(args.model)) != len(args.model):
        raise ValueError("specify at least two distinct provider names with --model")
    if any(name not in providers for name in args.model):
        raise ValueError("requested provider is not configured")
    nli = None
    if args.nli_config:
        value = json.loads(args.nli_config.read_text(encoding="utf-8"))
        for key in ("model_path", "tokenizer_path"):
            value[key] = Path(value[key])
        value["label_order"] = tuple(value["label_order"])
        nli = NliProxy(NliConfig(**value))
    runs = []
    for name in args.model:
        provider = LlamaProvider(providers[name])
        rows = []
        for case, evidence in cases:
            rows.append(await run_case(provider, case, evidence, nli))
            print(name, case["id"], rows[-1]["elapsed_ms"], flush=True)
        timings = sorted(row["elapsed_ms"] for row in rows)
        runs.append(
            {
                "provider": provider.config.public(),
                "provider_id": provider.config.identity,
                "cases": rows,
                "latency_ms": {
                    "median": statistics.median(timings) if timings else None,
                    "p95": timings[min(len(timings) - 1, int((len(timings) - 1) * 0.95))]
                    if timings
                    else None,
                },
            }
        )
    return {
        "schema_version": 1,
        "kind": "automatic-answer-evaluation",
        "dataset_sha256": _digest(args.dataset),
        "providers_sha256": _digest(args.providers),
        "dataset_kind": dataset.get("kind"),
        "question_count": len(cases),
        "human_review_count": 0,
        "quality_accepted": False,
        "nli_config_sha256": _digest(args.nli_config) if args.nli_config else None,
        "nli_status": "model_nli_automatic" if nli else "lexical_overlap_not_nli",
        "runs": runs,
    }


def export_reviews(report: dict, cases: list[dict]) -> dict:
    by_id = {case["id"]: case for case in cases}
    return {
        "schema_version": 1,
        "kind": "human-answer-review-packet",
        "dataset_sha256": report["dataset_sha256"],
        "rows": [
            {
                "question_id": result["question_id"],
                "question": by_id[result["question_id"]]["question"],
                "question_type": by_id[result["question_id"]].get("type"),
                "source_chunk_ids": by_id[result["question_id"]].get("source_chunk_ids", []),
                "reference_answer": by_id[result["question_id"]].get("expected_answer"),
                "provider_id": run["provider_id"],
                "answer": result.get("answer"),
                "effective_query": result.get("effective_query"),
                "evidence": result.get("evidence"),
                "failure": result.get("failure"),
                "automatic": result.get("automatic"),
                "human_claim_support": None,
                "human_citation_precision": None,
                "human_abstention_correct": None,
                "human_task_completion": None,
                "reviewer": None,
                "review_notes": "",
            }
            for run in report["runs"]
            for result in run["cases"]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--providers", type=Path, required=True)
    parser.add_argument("--model", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review-output", type=Path, required=True)
    parser.add_argument("--nli-config", type=Path)
    args = parser.parse_args()
    inputs = [args.dataset, args.providers, *([args.nli_config] if args.nli_config else [])]
    try:
        validate_outputs([args.output, args.review_output], inputs)
    except ValueError as error:
        parser.error(str(error))
    report = asyncio.run(evaluate(args))
    _, cases = load_cases(args.dataset)
    for path, data in (
        (args.output, report),
        (args.review_output, export_reviews(report, [case for case, _ in cases])),
    ):
        write_json(path, data)


if __name__ == "__main__":
    main()
