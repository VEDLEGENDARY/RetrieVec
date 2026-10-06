"""Provenance-bound answer evaluation; structural checks never imply semantic support."""

import math
import statistics
from datetime import datetime

from retrievec.corpus.snapshot import canonical, digest, parse_json
from retrievec.evaluation.load import percentile

KINDS = {"answerable", "partially_answerable", "unanswerable"}
SPLITS = {"development", "validation", "test"}


def load_dataset(path):
    value = parse_json(path.read_bytes())
    questions = value.get("questions", [])
    if value.get("schema_version") != 1 or len(questions) < 60:
        raise ValueError("a versioned dataset with at least 60 questions is required")
    if value.get("question_count") != len(questions):
        raise ValueError("question count differs")
    manifest_path = path.parent / value["corpus_manifest"]
    if manifest_path.is_symlink():
        raise ValueError("manifest cannot be a symlink")
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_relative_to(path.parent.resolve()):
        raise ValueError("manifest escapes dataset directory")
    manifest = parse_json(manifest_path.read_bytes())
    if digest(canonical(manifest)) != value["corpus_manifest_sha256"]:
        raise ValueError("fixed manifest changed")
    sources = {}
    for row in manifest["sources"]:
        source = path.parent / row["path"]
        if source.is_symlink() or not source.resolve().is_relative_to(path.parent.resolve()):
            raise ValueError("source escapes dataset directory")
        if digest(source.read_bytes()) != row["source_sha256"] or row["paper_id"] in sources:
            raise ValueError("source hash changed or identity duplicated")
        sources[row["paper_id"]] = row["source_sha256"]
    seen, texts, papers = set(), {}, {}
    for row in questions:
        if row["id"] in seen or row["kind"] not in KINDS or row["split"] not in SPLITS:
            raise ValueError("invalid or duplicate question")
        seen.add(row["id"])
        text = " ".join(row["question"].casefold().split())
        if not text or text in texts:
            raise ValueError("question text is empty or duplicated")
        texts[text] = row["split"]
        if row["judgment_provenance"] not in {"draft", "synthetic", "human-reviewed"}:
            raise ValueError("unknown judgment provenance")
        if row["judgment_provenance"] == "human-reviewed" and (
            not row.get("reviewer") or not row.get("reviewed_at")
        ):
            raise ValueError("human-reviewed question lacks reviewer provenance")
        for paper in row["source_paper_ids"]:
            if paper not in sources or papers.setdefault(paper, row["split"]) != row["split"]:
                raise ValueError("source missing or reused across splits")
    return value, sources


def binding(case):
    return {
        "question_sha256": digest(case["question"].encode()),
        "answer_sha256": digest(canonical(case["result"]["answer"])),
        "evidence_sha256": digest(canonical(case["result"]["evidence"])),
    }


def citation_pairs(case):
    answer = case["result"]["answer"]
    return [
        {"claim_id": claim["id"], "evidence_id": identity}
        for claim in answer["claims"]
        for identity in claim["evidence_ids"]
    ] + [
        {"claim_id": f"comparison-{index}", "evidence_id": identity}
        for index, comparison in enumerate(answer["comparisons"])
        for identity in comparison["evidence_ids"]
    ]


def blank_review(case):
    return {
        "case_id": case["case_id"],
        **binding(case),
        "reviewed": False,
        "reviewer": None,
        "reviewed_at": None,
        "citations": [
            {**row, "supported": None, "rationale": None} for row in citation_pairs(case)
        ],
        "faithfulness": None,
        "abstention_correct": None,
        "notes": None,
    }


def export_review(report):
    return {
        "schema_version": 1,
        "kind": "answer-human-review-packet",
        "dataset_sha256": report["dataset_sha256"],
        "split": report["split"],
        "rubric": {
            "supported": "Does the passage support this claim? An exact quote is insufficient.",
            "faithfulness": "0–1 fraction of claims supported by evidence; null for no claims.",
            "abstention_correct": "Was answering, partially answering, or abstaining justified?",
        },
        "cases": [
            {
                **blank_review(case),
                "question": case["question"],
                "answer": case["result"]["answer"],
                "evidence": case["result"]["evidence"],
            }
            for case in report["cases"]
            if case["state"] == "completed"
        ],
    }


def import_review(report, packet):
    if (
        packet.get("kind") != "answer-human-review-packet"
        or packet.get("schema_version") != 1
        or packet.get("dataset_sha256") != report["dataset_sha256"]
        or packet.get("split") != report["split"]
    ):
        raise ValueError("review packet does not match dataset/split")
    cases = {case["case_id"]: case for case in report["cases"] if case["state"] == "completed"}
    seen = set()
    for row in packet["cases"]:
        key = row["case_id"]
        if key not in cases or key in seen:
            raise ValueError("review case unknown or duplicated")
        seen.add(key)
        case = cases[key]
        if any(row.get(field) != value for field, value in binding(case).items()):
            raise ValueError("review refers to changed question, answer or evidence")
        if row.get("reviewed") is not True:
            continue
        if not isinstance(row.get("reviewer"), str) or not row["reviewer"].strip():
            raise ValueError("reviewer is required")
        if not isinstance(row.get("reviewed_at"), str):
            raise ValueError("review time is required")
        reviewed_at = datetime.fromisoformat(row["reviewed_at"].replace("Z", "+00:00"))
        if reviewed_at.tzinfo is None:
            raise ValueError("review time requires timezone")
        expected = {(item["claim_id"], item["evidence_id"]) for item in citation_pairs(case)}
        actual = [(item["claim_id"], item["evidence_id"]) for item in row["citations"]]
        if set(actual) != expected or len(actual) != len(expected):
            raise ValueError("review must assess every cited claim/passage pair exactly once")
        if any(
            type(item["supported"]) is not bool or not item.get("rationale")
            for item in row["citations"]
        ):
            raise ValueError("citation review requires a support decision and rationale")
        faithfulness = row.get("faithfulness")
        if (case["result"]["answer"]["claims"] or case["result"]["answer"]["comparisons"]) and (
            type(faithfulness) not in (float, int)
            or not math.isfinite(faithfulness)
            or not 0 <= faithfulness <= 1
        ):
            raise ValueError("faithfulness requires a finite score in [0,1]")
        if type(row.get("abstention_correct")) is not bool:
            raise ValueError("abstention review requires a decision")
        case["human_review"] = {
            key: row[key]
            for key in (
                "reviewer",
                "reviewed_at",
                "citations",
                "faithfulness",
                "abstention_correct",
                "notes",
            )
        }


def _mean(values):
    values = [value for value in values if value is not None]
    return statistics.mean(values) if values else None


def semantic_summary(cases, field):
    identity = "reviewer" if field == "human_review" else "judge_identity"
    reviewed = [case[field] for case in cases if case.get(field) and case[field].get(identity)]
    return {
        "assessed_case_count": len(reviewed),
        "citation_precision": _mean(
            [_mean([row["supported"] for row in review["citations"]]) for review in reviewed]
        ),
        "faithfulness": _mean([review.get("faithfulness") for review in reviewed]),
        "abstention_correctness": _mean([review.get("abstention_correct") for review in reviewed]),
    }


def summarize(report):
    summaries = {}
    for provider in report["providers"]:
        cases = [case for case in report["cases"] if case["provider"] == provider]
        completed = [case for case in cases if case["state"] == "completed"]
        latencies = [case["elapsed_ms"] for case in completed]
        ttft = [
            case["result"].get("timing", {}).get("worker_start_to_first_token_ms")
            for case in completed
        ]
        measured_ttft = [value for value in ttft if value is not None]
        automatic = []
        for case in completed:
            answer = case["result"]["answer"]
            automatic.append(
                (answer["status"] == "insufficient_evidence")
                == (case["question_kind"] == "unanswerable")
            )
        summaries[provider] = {
            "completed": len(completed),
            "failed": len(cases) - len(completed),
            "automatic_synthetic_abstention_correctness": _mean(automatic),
            "latency_ms": {"p50": percentile(latencies, 0.5), "p95": percentile(latencies, 0.95)},
            "ttft_worker_ms": {
                "samples": len(measured_ttft),
                "p50": percentile(measured_ttft, 0.5),
                "p95": percentile(measured_ttft, 0.95),
                "definition": "Worker start to first nonempty model content token; excludes queue.",
            },
            "human": semantic_summary(completed, "human_review"),
            "llm_judge": semantic_summary(completed, "llm_judge"),
        }
    report["summary"] = summaries
    paired = [
        case for case in report["cases"] if case.get("human_review") and case.get("llm_judge")
    ]
    agreement = []
    abstentions = []
    for case in paired:
        human, judge = case["human_review"], case["llm_judge"]
        human_pairs = {
            (r["claim_id"], r["evidence_id"]): r["supported"] for r in human["citations"]
        }
        for row in judge["citations"]:
            key = row["claim_id"], row["evidence_id"]
            if key in human_pairs:
                agreement.append(row["supported"] == human_pairs[key])
        abstentions.append(human["abstention_correct"] == judge["abstention_correct"])
    report["judge_vs_human"] = {
        "reviewed_case_count": len(paired),
        "citation_pair_count": len(agreement),
        "citation_support_agreement": _mean(agreement),
        "abstention_agreement": _mean(abstentions),
    }
    return report
