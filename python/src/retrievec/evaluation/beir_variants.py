"""Explicit offline fusion controls; no product defaults or score semantics change."""

import math


def _weight(value):
    if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("sparse weight must be finite and between zero and one")
    return float(value)


def _ranking(scores):
    return [
        {"chunk_id": key, "fusion_score": score, "rank": rank}
        for rank, (key, score) in enumerate(
            sorted(scores.items(), key=lambda row: (-row[1], row[0])), 1
        )
    ]


def weighted_rrf(sparse, dense, sparse_weight, k=60):
    weight = _weight(sparse_weight)
    if type(k) is not int or k < 1:
        raise ValueError("RRF k must be positive")
    scores = {}
    for ranking, leg_weight in ((sparse, weight), (dense, 1 - weight)):
        seen = set()
        for row in ranking:
            key = row["chunk_id"]
            if key in seen:
                continue
            seen.add(key)
            scores[key] = scores.get(key, 0) + leg_weight / (k + len(seen))
    return _ranking(scores)


def normalized_score(sparse, dense, sparse_weight):
    weight = _weight(sparse_weight)
    scores = {}
    for ranking, field, leg_weight in (
        (sparse, "score", weight),
        (dense, "cosine_score", 1 - weight),
    ):
        values = {}
        for row in ranking:
            key, value = row["chunk_id"], row.get(field, row.get("bm25_score"))
            if type(value) not in (float, int) or not math.isfinite(value):
                raise ValueError("fusion requires finite scores")
            values.setdefault(key, value)
        if not values:
            continue
        low, high = min(values.values()), max(values.values())
        for key, value in values.items():
            scaled = (value - low) / (high - low) if high != low else 1.0
            scores[key] = scores.get(key, 0) + leg_weight * scaled
    return _ranking(scores)


def fuse_variant(sparse, dense, config, limit=100):
    if config["family"] == "weighted_rrf":
        result = weighted_rrf(sparse, dense, config["sparse_weight"], config.get("k", 60))
    elif config["family"] == "normalized_score":
        result = normalized_score(sparse, dense, config["sparse_weight"])
    else:
        raise ValueError("unknown fusion family")
    return result[:limit]
