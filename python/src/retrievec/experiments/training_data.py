"""Provenance-aware reranker samples with fail-closed leakage checks."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from retrievec.corpus.snapshot import canonical, digest

Split = Literal["train", "development", "held_out"]


@dataclass(frozen=True)
class TrainingSample:
    sample_id: str
    query_id: str
    query: str
    query_cluster_id: str
    chunk_id: str
    passage: str
    passage_cluster_id: str
    paper_id: str
    paper_version_id: str
    split: Split
    grade: int
    review_status: Literal["reviewed", "draft", "pseudo"]
    reviewer: str | None
    judgment_id: str
    source_sha256: str
    provenance: Literal["human", "synthetic", "pseudo"]

    @classmethod
    def create(cls, **values) -> TrainingSample:
        identity = {key: value for key, value in values.items() if key != "sample_id"}
        expected = "ts_" + digest(canonical(identity))
        supplied = values.pop("sample_id", expected)
        if supplied != expected:
            raise ValueError("training sample identity mismatch")
        return cls(sample_id=supplied, **values)

    def validate(self) -> None:
        if self.split not in ("train", "development", "held_out"):
            raise ValueError("invalid training split")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                self.query_id,
                self.query,
                self.query_cluster_id,
                self.chunk_id,
                self.passage,
                self.passage_cluster_id,
                self.paper_id,
                self.paper_version_id,
                self.judgment_id,
                self.source_sha256,
            )
        ):
            raise ValueError("training sample fields must be nonempty strings")
        if type(self.grade) is not int or not 0 <= self.grade <= 3:
            raise ValueError("invalid relevance grade")
        if self.review_status == "reviewed" and not self.reviewer:
            raise ValueError("reviewed sample requires reviewer")
        if self.review_status != "reviewed" and self.reviewer is not None:
            raise ValueError("unreviewed sample cannot claim reviewer")
        if self.provenance == "human" and self.review_status != "reviewed":
            raise ValueError("human provenance requires reviewed judgment")
        if self.provenance != "human" and self.review_status == "reviewed":
            raise ValueError("generated provenance cannot claim human review")


def validate_samples(samples: Iterable[TrainingSample]) -> dict:
    rows = list(samples)
    if not rows:
        raise ValueError("training dataset is empty")
    sample_ids: set[str] = set()
    pair_ids: set[tuple[str, str]] = set()
    ownership: dict[tuple[str, str], Split] = {}
    for sample in rows:
        sample.validate()
        if sample.sample_id in sample_ids:
            raise ValueError("duplicate training sample")
        sample_ids.add(sample.sample_id)
        pair = (sample.query_id, sample.chunk_id)
        if pair in pair_ids:
            raise ValueError("duplicate query/passage judgment")
        pair_ids.add(pair)
        for kind, identity in (
            ("query", sample.query_cluster_id),
            ("passage", sample.passage_cluster_id),
            ("paper", sample.paper_id),
        ):
            key = (kind, identity)
            previous = ownership.setdefault(key, sample.split)
            if previous != sample.split:
                raise ValueError(f"{kind} cluster crosses frozen splits")
    counts = Counter((row.split, row.provenance, row.grade) for row in rows)
    return {
        "schema_version": 1,
        "dataset_id": "td_" + digest(canonical([row.__dict__ for row in rows])),
        "sample_count": len(rows),
        "counts": [
            {"split": key[0], "provenance": key[1], "grade": key[2], "count": value}
            for key, value in sorted(counts.items())
        ],
    }


def training_pairs(samples: Iterable[TrainingSample]) -> list[TrainingSample]:
    rows = list(samples)
    validate_samples(rows)
    return [
        row
        for row in rows
        if row.split == "train" and row.provenance == "human" and row.review_status == "reviewed"
    ]
