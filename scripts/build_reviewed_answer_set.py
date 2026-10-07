"""Promote explicitly reviewed PDF passage questions into a versioned answer set."""

import argparse
import hashlib
import json
from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest

TYPES = {"single_fact", "numeric", "comparison", "unanswerable"}


def build(packet: dict, *, min_questions: int = 50) -> dict:
    if packet.get("schema_version") != 1 or packet.get("kind") != "pdf-passage-review-packet":
        raise ValueError("expected versioned PDF passage review packet")
    candidates = packet.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("PDF review candidates missing")
    by_chunk = {row["chunk_id"]: row for row in candidates}
    if len(by_chunk) != len(candidates):
        raise ValueError("duplicate PDF passage chunk")
    questions = []
    for row in candidates:
        if row.get("review_status") != "reviewed":
            continue
        question_type = row.get("question_type")
        source_ids = row.get("source_chunk_ids", [row["chunk_id"]])
        if (
            question_type not in TYPES
            or not isinstance(source_ids, list)
            or not source_ids
            or len(set(source_ids)) != len(source_ids)
            or not set(source_ids) <= set(by_chunk)
            or not all(
                isinstance(row.get(field), str) and row[field].strip()
                for field in ("question", "expected_answer", "reviewer", "review_rationale")
            )
        ):
            raise ValueError(f"reviewed PDF question {row['candidate_id']} is incomplete")
        if hashlib.sha256(row["passage"].encode()).hexdigest() != row["text_sha256"]:
            raise ValueError("reviewed passage text changed")
        evidence = []
        for chunk_id in source_ids:
            source = by_chunk[chunk_id]
            if hashlib.sha256(source["passage"].encode()).hexdigest() != source["text_sha256"]:
                raise ValueError("supporting passage text changed")
            evidence.append(
                {
                    "chunk_id": chunk_id,
                    "paper_id": source["paper_id"],
                    "title": source["paper_title"],
                    "page_range": source["page_range"],
                    "text": source["passage"],
                    "source_sha256": source["source_sha256"],
                }
            )
        questions.append(
            {
                "id": row["candidate_id"],
                "question": row["question"],
                "type": question_type,
                "unanswerable": question_type == "unanswerable",
                "expected_answer": row["expected_answer"],
                "source_chunk_ids": source_ids,
                "evidence": evidence,
                "reviewer": row["reviewer"],
                "review_rationale": row["review_rationale"],
            }
        )
    if len(questions) < min_questions:
        raise ValueError(
            f"only {len(questions)} reviewed questions; at least {min_questions} required"
        )
    if {row["type"] for row in questions} != TYPES:
        raise ValueError("reviewed set must cover all four question types")
    identity = {
        "schema_version": 1,
        "kind": "reviewed-pdf-oracle-evidence-answer-set",
        "corpus_snapshot_id": packet["corpus_snapshot_id"],
        "manifest_sha256": packet["manifest_sha256"],
        "questions": questions,
        "question_count": len(questions),
        "retrieval_evaluated": False,
    }
    return dict(identity, dataset_id="aq_" + digest(canonical(identity)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-questions", type=int, default=50)
    args = parser.parse_args()
    if not 1 <= args.min_questions <= 100:
        parser.error("min-questions must be between 1 and 100")
    result = build(
        json.loads(args.packet.read_text(encoding="utf-8")), min_questions=args.min_questions
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(result) + b"\n")


if __name__ == "__main__":
    main()
