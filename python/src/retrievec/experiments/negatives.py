"""Training-only hard-negative mining that never treats unjudged hits as negatives."""

from __future__ import annotations

import random
from collections import defaultdict

from retrievec.corpus.snapshot import canonical, digest
from retrievec.experiments.training_data import TrainingSample, validate_samples


def mine_hard_negatives(
    samples: list[TrainingSample],
    ranked_pools: list[dict],
    *,
    per_query: int = 4,
    seed: int = 1729,
) -> dict:
    validate_samples(samples)
    if not 1 <= per_query <= 64:
        raise ValueError("invalid hard-negative cap")
    by_pair = {(row.query_id, row.chunk_id): row for row in samples}
    split_by_query: dict[str, set[str]] = defaultdict(set)
    for row in samples:
        split_by_query[row.query_id].add(row.split)
    selected, excluded = [], []
    rng = random.Random(seed)
    for pool in sorted(ranked_pools, key=lambda value: value["query_id"]):
        query_id = pool["query_id"]
        if split_by_query.get(query_id) != {"train"}:
            excluded.append({"query_id": query_id, "reason": "not_training_only"})
            continue
        eligible = []
        for rank, candidate in enumerate(pool["candidates"], 1):
            sample = by_pair.get((query_id, candidate["chunk_id"]))
            if sample is None:
                excluded.append({"query_id": query_id, "chunk_id": candidate["chunk_id"], "reason": "unjudged"})
            elif sample.review_status != "reviewed" or sample.provenance != "human":
                excluded.append({"query_id": query_id, "chunk_id": sample.chunk_id, "reason": "uncertain"})
            elif sample.grade != 0:
                excluded.append({"query_id": query_id, "chunk_id": sample.chunk_id, "reason": "not_negative"})
            else:
                eligible.append({"sample_id": sample.sample_id, "query_id": query_id, "chunk_id": sample.chunk_id, "rank": rank})
        rng.shuffle(eligible)
        selected.extend(sorted(eligible[:per_query], key=lambda row: row["rank"]))
    identity = {
        "schema_version": 1,
        "dataset_id": "td_" + digest(canonical([row.__dict__ for row in samples])),
        "pool_hash": digest(canonical(ranked_pools)),
        "per_query": per_query,
        "seed": seed,
        "selected": selected,
        "excluded": excluded,
    }
    return dict(identity, mining_id="hn_" + digest(canonical(identity)))
