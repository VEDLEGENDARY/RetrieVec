"""Record one explicit human answer review without modifying automatic scores."""

import argparse
import json
import os
from pathlib import Path


def rating(value: str) -> bool:
    if value not in ("yes", "no"):
        raise argparse.ArgumentTypeError("use yes or no")
    return value == "yes"


def update(packet: dict, args: argparse.Namespace) -> dict:
    if packet.get("kind") != "human-answer-review-packet" or packet.get("schema_version") != 1:
        raise ValueError("unsupported answer review packet")
    matches = [
        row
        for row in packet["rows"]
        if row["question_id"] == args.question_id and row["provider_id"] == args.provider_id
    ]
    if len(matches) != 1:
        raise ValueError("review target must match exactly one answer")
    row = matches[0]
    if row["reviewer"] is not None:
        raise ValueError("existing human review cannot be overwritten")
    if not args.reviewer.strip() or not args.notes.strip():
        raise ValueError("reviewer and rationale are required")
    row.update(
        human_claim_support=args.claim_support,
        human_citation_precision=args.citation_precision,
        human_abstention_correct=args.abstention_correct,
        human_task_completion=args.task_completion,
        reviewer=args.reviewer.strip(),
        review_notes=args.notes.strip(),
    )
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--question-id", required=True)
    parser.add_argument("--provider-id", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--notes", required=True)
    for field in (
        "claim-support",
        "citation-precision",
        "abstention-correct",
        "task-completion",
    ):
        parser.add_argument(f"--{field}", type=rating, required=True)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    updated = update(packet, args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    staging = args.output.with_suffix(args.output.suffix + ".tmp")
    with staging.open("w", encoding="utf-8") as stream:
        json.dump(updated, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(staging, args.output)


if __name__ == "__main__":
    main()
