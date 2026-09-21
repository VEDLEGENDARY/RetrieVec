"""Freeze genuinely reviewed labels and reject previously exposed held-out questions."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest
from retrievec.evaluation.dataset import load_dataset


def normalize(question):
    return " ".join(question.casefold().split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--prior-dataset", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.dataset.read_bytes()
    dataset = load_dataset(args.dataset, args.corpus, require_reviewed=True)
    prior_hashes, prior_questions, prior_ids = [], set(), set()
    for path in args.prior_dataset:
        previous = path.read_bytes()
        prior_hashes.append(digest(previous))
        for query in json.loads(previous)["queries"]:
            prior_questions.add(normalize(query["query"]))
            prior_ids.add(query["query_id"])
    held = [query for query in dataset["queries"] if query["split"] == "held_out"]
    if not held:
        raise ValueError("a frozen release evaluation requires held-out questions")
    if any(
        query["query_id"] in prior_ids or normalize(query["query"]) in prior_questions
        for query in held
    ):
        raise ValueError("held-out questions overlap a supplied previously inspected set")
    if len({normalize(query["query"]) for query in dataset["queries"]}) != len(dataset["queries"]):
        raise ValueError("duplicate normalized questions")
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "dataset.json").write_bytes(raw)
    manifest = {
        "schema_version": 1,
        "dataset_id": dataset["dataset_id"],
        "dataset_sha256": digest(raw),
        "prior_dataset_sha256": sorted(prior_hashes),
        "corpus_snapshot_id": dataset["corpus_snapshot_id"],
        "created_at": datetime.now(UTC).isoformat(),
        "query_count": len(dataset["queries"]),
        "held_out_count": len(held),
        "judgment_count": len(dataset["judgments"]),
        "reviewers": sorted({row["reviewer"] for row in dataset["judgments"]}),
        "limitation": "Reviewer provenance is supplied, not independently verified. "
        "Only supplied prior sets are checked; paraphrases require human inspection.",
    }
    (args.output / "freeze.json").write_bytes(canonical(manifest) + b"\n")


if __name__ == "__main__":
    main()
