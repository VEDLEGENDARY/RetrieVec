"""Bounded reranker baselines and deterministic candidate-pool evaluation."""

from __future__ import annotations

import hashlib
import math
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from importlib.metadata import version
from typing import Protocol

import numpy as np

from retrievec.corpus.snapshot import canonical, digest
from retrievec.evaluation.metrics import aggregate, metrics
from retrievec.evaluation.paired import compare

PRETRAINED_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
PRETRAINED_REVISION = "9cc09816f0a7a8aaceefa40a3cfbb843c1bfa579"


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


class OnnxCrossEncoder:
    """Offline, pinned CPU reranker; loading cannot silently fetch a newer model."""

    def __init__(self, config: RerankerConfig, *, batch_size: int = 8):
        if not 1 <= batch_size <= 32:
            raise ValueError("invalid reranker batch size")
        config.validate()
        if len(config.revision) != 40 or any(c not in "0123456789abcdef" for c in config.revision):
            raise ValueError("reranker requires a full immutable commit revision")
        if config.tokenizer_revision != config.revision or config.scoring != "single_logit":
            raise ValueError("unsupported pretrained model contract")
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        tokenizer_path = hf_hub_download(
            config.model,
            "tokenizer.json",
            revision=config.tokenizer_revision,
            local_files_only=True,
        )
        model_path = hf_hub_download(
            config.model,
            "onnx/model.onnx",
            revision=config.revision,
            local_files_only=True,
        )
        self.tokenizer = Tokenizer.from_file(tokenizer_path)
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            model_path, sess_options=options, providers=["CPUExecutionProvider"]
        )
        names = {item.name for item in self.session.get_inputs()}
        if (
            not names <= {"input_ids", "attention_mask", "token_type_ids"}
            or not {"input_ids", "attention_mask"} <= names
        ):
            raise ValueError("unexpected reranker model inputs")
        self.input_names = names
        self.batch_size = batch_size
        self.config = config

        def sha256(path):
            with open(path, "rb") as source:
                return hashlib.file_digest(source, "sha256").hexdigest()

        self.artifacts = {
            "model_sha256": sha256(model_path),
            "tokenizer_sha256": sha256(tokenizer_path),
            "software": {
                name: version(name)
                for name in ("onnxruntime", "tokenizers", "numpy", "huggingface-hub")
            },
            "provider": "CPUExecutionProvider",
        }

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not 1 <= len(pairs) <= 1000 or any(
            not query.strip() or not passage.strip() for query, passage in pairs
        ):
            raise ValueError("reranker requires 1-1000 nonempty query/passage pairs")
        scores = []
        for start in range(0, len(pairs), self.batch_size):
            batch = pairs[start : start + self.batch_size]
            encoded = [
                self.tokenizer.encode(
                    self.config.query_prefix + query,
                    self.config.passage_prefix + passage,
                )
                for query, passage in batch
            ]
            if any(len(row.ids) > self.config.max_tokens for row in encoded):
                raise ValueError("reranker input exceeds pinned token budget")
            width = max(len(row.ids) for row in encoded)
            ids = np.zeros((len(batch), width), dtype=np.int64)
            masks = np.zeros_like(ids)
            types = np.zeros_like(ids)
            for index, row in enumerate(encoded):
                ids[index, : len(row.ids)] = row.ids
                masks[index, : len(row.ids)] = row.attention_mask
                types[index, : len(row.ids)] = row.type_ids
            inputs = {"input_ids": ids, "attention_mask": masks, "token_type_ids": types}
            logits = np.asarray(
                self.session.run(None, {name: inputs[name] for name in self.input_names})[0]
            )
            if logits.shape not in ((len(batch),), (len(batch), 1)):
                raise ValueError("unexpected reranker score shape")
            values = logits.reshape(-1)
            if not np.isfinite(values).all():
                raise ValueError("nonfinite reranker scores")
            scores.extend(float(value) for value in values)
        return scores


def pretrained_config() -> RerankerConfig:
    return RerankerConfig(
        name="ms-marco-minilm-l6-v2-onnx",
        model=PRETRAINED_MODEL,
        revision=PRETRAINED_REVISION,
        tokenizer_revision=PRETRAINED_REVISION,
        max_tokens=512,
        query_prefix="",
        passage_prefix="",
    )


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


def evaluate_pool_sweep(
    pools: Iterable[dict],
    judgments: dict[str, dict[str, int]],
    model: Reranker,
    *,
    sizes: tuple[int, ...] = (20, 50, 100),
    top_k: int = 10,
    judgment_unit: str = "chunk_id",
) -> dict:
    """Measure reranking over identical pinned candidate prefixes at each size."""
    if (
        sizes != (20, 50, 100)
        or not 1 <= top_k <= 20
        or judgment_unit not in ("chunk_id", "paper_id")
    ):
        raise ValueError("unsupported reranker sweep")
    pools = list(pools)
    if not pools or len({pool.get("query_id") for pool in pools}) != len(pools):
        raise ValueError("candidate pools require distinct query IDs")
    outputs = {}
    pool_hashes = [digest(canonical(pool)) for pool in pools]
    for size in sizes:
        base_rows, ranked_rows, latencies, recalls, failures = [], [], [], [], []
        paired_ids = []
        for pool in pools:
            query_id = pool["query_id"]
            candidates = pool["candidates"][:size]
            if not candidates:
                failures.append({"query_id": query_id, "error": "empty_pool"})
                continue
            qrels = judgments.get(query_id, {})
            positives = {
                identity
                for identity, grade in qrels.items()
                if grade >= (1 if judgment_unit == "paper_id" else 2)
            }
            recalls.append(
                len(positives & {row[judgment_unit] for row in candidates}) / len(positives)
                if positives
                else None
            )
            try:
                ranked, elapsed = rerank(
                    pool["query"],
                    candidates,
                    model,
                    top_k=len(candidates)
                    if judgment_unit == "paper_id"
                    else min(top_k, len(candidates)),
                )
                if judgment_unit == "paper_id":
                    from retrievec.evaluation.beir_eval import score

                    def documents(rows, excluded=query_id):
                        return list(
                            dict.fromkeys(
                                row["paper_id"] for row in rows if row["paper_id"] != excluded
                            )
                        )

                    base_rows.append(score(documents(candidates), qrels))
                    ranked_rows.append(score(documents(ranked), qrels))
                else:
                    base_rows.append(metrics([row["chunk_id"] for row in candidates], qrels, top_k))
                    ranked_rows.append(metrics([row["chunk_id"] for row in ranked], qrels, top_k))
                latencies.append(elapsed)
                paired_ids.append(query_id)
            except (ValueError, OSError, RuntimeError) as error:
                failures.append({"query_id": query_id, "error": type(error).__name__})
        ordered = sorted(latencies)
        if judgment_unit == "paper_id":

            def paper_summary(rows):
                return {
                    key: {"mean": sum(row[key] for row in rows) / len(rows) if rows else None}
                    for key in ("ndcg", "mrr", "recall", "coverage")
                }

            baseline = paper_summary(base_rows)
            reranked = paper_summary(ranked_rows)
        else:
            baseline = aggregate(base_rows)
            reranked = aggregate(ranked_rows)
        before, after = baseline["ndcg"]["mean"], reranked["ndcg"]["mean"]
        p50 = ordered[len(ordered) // 2] if ordered else None
        p95 = ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.95))] if ordered else None

        def paired_report(rows, ids=paired_ids, errors=failures):
            per_query = [dict(row, query_id=qid) for qid, row in zip(ids, rows, strict=True)]
            return {
                "schema_version": 1,
                "dataset_id": digest(canonical(pool_hashes)),
                "split": "candidate_pool",
                "cutoff": 10 if judgment_unit == "paper_id" else top_k,
                "includes_drafts": False,
                "per_query": per_query,
                "failures": errors,
                "missing_queries": [],
                "results_sha256": digest(canonical(per_query)),
            }

        outputs[str(size)] = {
            "baseline": baseline,
            "reranked": reranked,
            "paired_vs_plain_hybrid": compare(paired_report(base_rows), paired_report(ranked_rows)),
            "candidate_recall": sum(value for value in recalls if value is not None)
            / sum(value is not None for value in recalls)
            if any(value is not None for value in recalls)
            else None,
            "rerank_latency_ms": {"p50": p50, "p95": p95, "samples": len(ordered)},
            "ndcg_gain_per_ms_p50": (after - before) / p50
            if before is not None and after is not None and p50
            else None,
            "failures": failures,
        }
    return {
        "schema_version": 1,
        "kind": "candidate-pool-reranker-sweep",
        "model": asdict(model.config),
        "model_artifacts": getattr(model, "artifacts", None),
        "pool_hashes": [digest(canonical(pool)) for pool in pools],
        "judgment_unit": judgment_unit,
        "sizes": outputs,
        "default_changed": False,
    }
