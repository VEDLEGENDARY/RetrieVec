"""Exhaustive cosine search in bounded blocks with stable external-ID ties."""

import numpy as np

from retrievallab.dense.model import normalize


def exact_search(vectors, chunk_ids: list[str], query, limit: int = 100, block_size: int = 4096) -> list[dict]:
    if type(limit) is not int or not 1 <= limit <= 1000 or type(block_size) is not int or not 1 <= block_size <= 65536:
        raise ValueError("invalid dense search bounds")
    query = np.asarray(query, dtype=np.float32)
    if vectors.ndim != 2 or query.ndim != 1 or vectors.shape != (len(chunk_ids), len(query)) or len(set(chunk_ids)) != len(chunk_ids) or any(not isinstance(key, str) or not key for key in chunk_ids):
        raise ValueError("dense vector dimensions or IDs differ")
    query = normalize(query.reshape(1, -1))[0]
    best = []
    for start in range(0, len(chunk_ids), block_size):
        block = vectors[start:start + block_size]
        if not np.isfinite(block).all() or not np.allclose(np.linalg.norm(block.astype(np.float64), axis=1), 1, atol=1e-5, rtol=0):
            raise ValueError("document vectors must be finite and normalized")
        scores = block @ query
        if not np.isfinite(scores).all():
            raise ValueError("nonfinite cosine scores")
        candidates = [(float(score), chunk_ids[start + offset]) for offset, score in enumerate(scores)]
        best = sorted(best + candidates, key=lambda item: (-item[0], item[1]))[:limit]
    return [{"chunk_id": key, "cosine_score": score, "rank": rank} for rank, (score, key) in enumerate(best, 1)]
