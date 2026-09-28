"""Bounded reranker baselines and deterministic candidate-pool evaluation."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from typing import Protocol

from retrievec.corpus.snapshot import canonical, digest
from retrievec.evaluation.metrics import aggregate, metrics


@dataclass(frozen=True)
class RerankerConfig:
    name: str
    model: str
    revision: str
    tokenizer_revision: str
    max_tokens: int
    query_prefix: str
    passage_prefix: str
    pair_order: str = "query_passage"
    scoring: str = "single_logit"
    truncation: str = "reject"
    enabled_by_default: bool = False

    def validate(self) -> None:
        if not all((self.name, self.model, self.revision, self.tokenizer_revision)):
            raise ValueError("reranker identity must be pinned")
        if not 8 <= self.max_tokens <= 8192:
            raise ValueError("invalid reranker input limit")
        if self.pair_order != "query_passage" or self.truncation != "reject":
            raise ValueError("unsupported reranker input contract")
        if self.enabled_by_default:
            raise ValueError("experimental reranker cannot be a default")

    @property
    def config_id(self) -> str:
        self.validate()
        return "rr_" + digest(canonical(asdict(self)))


class Reranker(Protocol):
    config: RerankerConfig

    def score(self, pairs: list[tuple[str, str]]) -> list[float]: ...


class CallableReranker:
    def __init__(
        self, config: RerankerConfig, scorer: Callable[[list[tuple[str, str]]], list[float]]
    ):
        config.validate()
        self.config = config
        self._scorer = scorer

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not pairs or len(pairs) > 1000:
            raise ValueError("reranker batch requires 1-1000 pairs")
        if any(not query.strip() or not passage.strip() for query, passage in pairs):
            raise ValueError("reranker text cannot be empty")
        scores = self._scorer(pairs)
        if len(scores) != len(pairs) or any(not math.isfinite(value) for value in scores):
            raise ValueError("reranker returned invalid scores")
        return [float(value) for value in scores]


def rerank(
    query: str, candidates: list[dict], model: Reranker, *, top_k: int
) -> tuple[list[dict], float]:
    if not 1 <= top_k <= len(candidates) <= 1000:
        raise ValueError("invalid reranker candidate bounds")
    ids = [row.get("chunk_id") for row in candidates]
    if any(not isinstance(identity, str) or not identity for identity in ids) or len(
        set(ids)
    ) != len(ids):
        raise ValueError("candidate IDs must be unique")
    start = time.perf_counter()
    scores = model.score([(query, row["text"]) for row in candidates])
    ranked = [
        dict(row, reranker_score=score) for row, score in zip(candidates, scores, strict=True)
    ]
    ranked.sort(key=lambda row: (-row["reranker_score"], row["chunk_id"]))
    return ranked[:top_k], (time.perf_counter() - start) * 1000


def evaluate_baseline(
    pools: Iterable[dict],
    judgments: dict[str, dict[str, int]],
    model: Reranker,
    *,
    top_k: int = 10,
) -> dict:
    rows, elapsed, failures = [], [], []
    pool_hashes = []
    for pool in pools:
        query_id, query = pool["query_id"], pool["query"]
        candidates = pool["candidates"]
        pool_hashes.append(digest(canonical(pool)))
        try:
            ranked, latency = rerank(query, candidates, model, top_k=min(top_k, len(candidates)))
            rows.append(
                metrics([row["chunk_id"] for row in ranked], judgments.get(query_id, {}), top_k)
            )
            elapsed.append(latency)
        except Exception as error:
            failures.append({"query_id": query_id, "error": type(error).__name__})
    ordered = sorted(elapsed)

    def percentile(q):
        return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * q))] if ordered else None

    return {
        "schema_version": 1,
        "configuration": asdict(model.config),
        "configuration_id": model.config.config_id,
        "candidate_pool_hashes": pool_hashes,
        "metrics": aggregate(rows),
        "latency_ms": {"p50": percentile(0.50), "p95": percentile(0.95), "samples": len(elapsed)},
        "failures": failures,
        "quality_evidence": bool(rows) and not failures,
    }
