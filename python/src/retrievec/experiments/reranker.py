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
from retrievec.evaluation.beir_eval import score as paper_metrics
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
        try:
            self.session = ort.InferenceSession(
                model_path, sess_options=options, providers=["CPUExecutionProvider"]
            )
        except Exception as error:
            # Native ONNX exceptions do not share Python's RuntimeError base.
            raise RuntimeError("reranker model could not be loaded") from error
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
            try:
                output = self.session.run(None, {name: inputs[name] for name in self.input_names})
            except Exception as error:
                # Normalize only the external runtime call; preserve its cause for diagnosis.
                raise RuntimeError("reranker inference failed") from error
            logits = np.asarray(output[0])
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
    if type(top_k) is not int or not 1 <= top_k <= len(candidates) <= 1000:
        raise ValueError("invalid reranker candidate bounds")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("reranker query cannot be empty")
    if any(not isinstance(row.get("text"), str) or not row["text"].strip() for row in candidates):
        raise ValueError("candidate text cannot be empty")
    ids = [row.get("chunk_id") for row in candidates]
    if any(not isinstance(identity, str) or not identity for identity in ids) or len(
        set(ids)
    ) != len(ids):
        raise ValueError("candidate IDs must be unique")
    start = time.perf_counter()
    scores = model.score([(query, row["text"]) for row in candidates])
    if len(scores) != len(candidates) or any(
        not isinstance(value, (int, float)) or not math.isfinite(value) for value in scores
    ):
        raise ValueError("reranker returned invalid scores")
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
        except (ValueError, OSError, RuntimeError) as error:
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
        "quality_evidence": bool(rows)
        and not failures
        and all(row["ndcg"] is not None for row in rows),
    }


def _candidate_metrics(candidates, query_id, judgments, judgment_unit, top_k):
    if judgment_unit == "paper_id":
        documents = list(
            dict.fromkeys(row["paper_id"] for row in candidates if row["paper_id"] != query_id)
        )
        return paper_metrics(documents, judgments)
    return metrics([row["chunk_id"] for row in candidates], judgments, top_k)


def _paired_report(rows, failures, dataset_id, cutoff):
    return {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "split": "candidate_pool",
        "cutoff": cutoff,
        "includes_drafts": False,
        "per_query": rows,
        "failures": failures,
        "missing_queries": [],
        "results_sha256": digest(canonical(rows)),
    }


def _summary(rows, judgment_unit):
    if judgment_unit == "chunk_id":
        return aggregate(rows)
    return {
        key: {"mean": sum(row[key] for row in rows) / len(rows) if rows else None}
        for key in ("ndcg", "mrr", "recall", "coverage")
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
    """Compare each reranker run with its independently measured hybrid baseline."""
    if (
        sizes != (20, 50, 100)
        or type(top_k) is not int
        or not 1 <= top_k <= 20
        or judgment_unit not in ("chunk_id", "paper_id")
        or (judgment_unit == "paper_id" and top_k != 10)
    ):
        raise ValueError("unsupported reranker sweep")
    pools = list(pools)
    ids = [pool.get("query_id") for pool in pools]
    if not pools or any(not isinstance(qid, str) or not qid.strip() for qid in ids):
        raise ValueError("candidate pools require nonempty query IDs")
    if len(set(ids)) != len(ids):
        raise ValueError("candidate pools require distinct query IDs")
    outputs = {}
    pool_hashes = [digest(canonical(pool)) for pool in pools]
    dataset_id = digest(canonical(pool_hashes))
    for size in sizes:
        base_rows, ranked_rows, latencies, recalls = [], [], [], []
        base_failures, failures = [], []
        for pool in pools:
            query_id = pool["query_id"]
            candidates = pool["candidates"][:size]
            qrels = judgments.get(query_id, {})
            try:
                if not candidates:
                    raise ValueError("empty_pool")
                before = _candidate_metrics(candidates, query_id, qrels, judgment_unit, top_k)
                base_rows.append(dict(before, query_id=query_id))
            except ValueError as error:
                failure = {"query_id": query_id, "error": type(error).__name__}
                base_failures.append(failure)
                failures.append(failure)
                continue
            positives = {
                identity
                for identity, grade in qrels.items()
                if grade >= (1 if judgment_unit == "paper_id" else 2)
            }
            available = {row[judgment_unit] for row in candidates}
            if judgment_unit == "paper_id":
                available.discard(query_id)
            recalls.append(len(positives & available) / len(positives) if positives else None)
            try:
                ranked, elapsed = rerank(pool["query"], candidates, model, top_k=len(candidates))
                after = _candidate_metrics(ranked, query_id, qrels, judgment_unit, top_k)
                ranked_rows.append(dict(after, query_id=query_id))
                latencies.append(elapsed)
            except (ValueError, OSError, RuntimeError) as error:
                failures.append({"query_id": query_id, "error": type(error).__name__})
        baseline = _summary(base_rows, judgment_unit)
        reranked = _summary(ranked_rows, judgment_unit)
        paired = compare(
            _paired_report(base_rows, base_failures, dataset_id, top_k),
            _paired_report(ranked_rows, failures, dataset_id, top_k),
        )
        ordered = sorted(latencies)
        p50 = ordered[len(ordered) // 2] if ordered else None
        p95 = ordered[int((len(ordered) - 1) * 0.95)] if ordered else None
        gain = paired["metrics"]["ndcg"]["mean_delta_right_minus_left"]
        defined_recalls = [value for value in recalls if value is not None]
        outputs[str(size)] = {
            "baseline": baseline,
            "reranked": reranked,
            "paired_vs_plain_hybrid": paired,
            "candidate_recall": sum(defined_recalls) / len(defined_recalls)
            if defined_recalls
            else None,
            "rerank_latency_ms": {"p50": p50, "p95": p95, "samples": len(ordered)},
            "ndcg_gain_per_ms_p50": gain / p50 if gain is not None and p50 else None,
            "baseline_failures": base_failures,
            "failures": failures,
        }
    return {
        "schema_version": 1,
        "kind": "candidate-pool-reranker-sweep",
        "model": asdict(model.config),
        "model_artifacts": getattr(model, "artifacts", None),
        "pool_hashes": pool_hashes,
        "judgment_unit": judgment_unit,
        "sizes": outputs,
        "default_changed": False,
    }
