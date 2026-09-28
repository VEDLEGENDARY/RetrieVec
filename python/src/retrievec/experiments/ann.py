"""Snapshot-scoped IVF cosine experiment with exact-search fallback."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass

import numpy as np

from retrievec.corpus.snapshot import canonical, digest
from retrievec.dense.model import normalize
from retrievec.dense.search import exact_search


@dataclass(frozen=True)
class IVFConfig:
    clusters: int = 64
    probes: int = 8
    iterations: int = 12
    seed: int = 1729
    enabled_by_default: bool = False

    def validate(self, count: int) -> None:
        if self.enabled_by_default:
            raise ValueError("approximate retrieval cannot be enabled by default")
        if not 1 <= self.clusters <= min(count, 4096):
            raise ValueError("invalid IVF cluster count")
        if not 1 <= self.probes <= self.clusters or not 1 <= self.iterations <= 100:
            raise ValueError("invalid IVF search/build parameters")


class IVFIndex:
    """A deterministic research adapter; exact cosine remains authoritative."""

    def __init__(
        self, vectors: np.ndarray, chunk_ids: list[str], snapshot_id: str, config: IVFConfig
    ):
        values = normalize(vectors)
        if len(values) != len(chunk_ids) or not snapshot_id.startswith("rs_"):
            raise ValueError("ANN vectors, IDs or snapshot are invalid")
        if len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("ANN chunk IDs must be unique")
        config.validate(len(values))
        self.vectors = values
        self.chunk_ids = list(chunk_ids)
        self.snapshot_id = snapshot_id
        self.config = config
        self._build()

    def _build(self) -> None:
        rng = np.random.default_rng(self.config.seed)
        seeds = rng.choice(len(self.vectors), size=self.config.clusters, replace=False)
        centers = self.vectors[seeds].copy()
        assignments = np.zeros(len(self.vectors), dtype=np.int32)
        for _ in range(self.config.iterations):
            assignments = np.argmax(self.vectors @ centers.T, axis=1).astype(np.int32)
            next_centers = centers.copy()
            for cluster in range(self.config.clusters):
                members = self.vectors[assignments == cluster]
                if len(members):
                    next_centers[cluster] = normalize(members.mean(axis=0, keepdims=True))[0]
            if np.array_equal(np.argmax(self.vectors @ next_centers.T, axis=1), assignments):
                centers = next_centers
                break
            centers = next_centers
        self.centers = centers
        self.members = [
            np.flatnonzero(assignments == cluster) for cluster in range(self.config.clusters)
        ]
        identity = {
            "schema_version": 1,
            "snapshot_id": self.snapshot_id,
            "configuration": asdict(self.config),
            "chunk_ids_hash": digest(canonical(self.chunk_ids)),
            "vectors_hash": digest(self.vectors.astype("<f4").tobytes()),
        }
        self.index_id = "ai_" + digest(canonical(identity))

    def search(self, query: np.ndarray, *, top_k: int, snapshot_id: str) -> list[dict]:
        if snapshot_id != self.snapshot_id:
            raise ValueError("ANN query snapshot mismatch")
        vector = normalize(np.asarray(query, dtype=np.float32).reshape(1, -1))[0]
        if vector.shape[0] != self.vectors.shape[1] or not 1 <= top_k <= len(self.vectors):
            raise ValueError("invalid ANN query dimensions or bounds")
        clusters = np.argsort(-(self.centers @ vector), kind="stable")[: self.config.probes]
        candidates = np.unique(np.concatenate([self.members[index] for index in clusters]))
        if not len(candidates):
            return []
        scores = self.vectors[candidates] @ vector
        order = sorted(
            range(len(candidates)),
            key=lambda at: (-float(scores[at]), self.chunk_ids[int(candidates[at])]),
        )[:top_k]
        return [
            {
                "chunk_id": self.chunk_ids[int(candidates[at])],
                "cosine_score": float(scores[at]),
                "index_id": self.index_id,
            }
            for at in order
        ]

    def exact(self, query: np.ndarray, *, top_k: int) -> list[dict]:
        return exact_search(self.vectors, self.chunk_ids, query, top_k)


def timed_search(
    index: IVFIndex, query: np.ndarray, *, top_k: int, snapshot_id: str
) -> tuple[list[dict], float]:
    started = time.perf_counter()
    result = index.search(query, top_k=top_k, snapshot_id=snapshot_id)
    return result, (time.perf_counter() - started) * 1000
