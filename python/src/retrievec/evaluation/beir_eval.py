"""Frozen development selection and held-out document metrics for BEIR."""

import itertools
import math
import statistics

from retrievec.corpus.snapshot import canonical, digest
from retrievec.evaluation.load import percentile
from retrievec.evaluation.paired import compare


def score(ranking, judgments):
    positive = {key for key, grade in judgments.items() if grade > 0}
    if not positive or len(set(ranking)) != len(ranking):
        raise ValueError("evaluation requires positives and unique document IDs")
    dcg = sum(1 / math.log2(i + 2) for i, key in enumerate(ranking[:10]) if key in positive)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(10, len(positive))))
    return {
        "ndcg": dcg / ideal,
        "mrr": next((1 / i for i, key in enumerate(ranking[:10], 1) if key in positive), 0),
        "recall": len(set(ranking[:100]) & positive) / len(positive),
        "coverage": sum(key in judgments for key in ranking) / len(ranking) if ranking else 0,
    }


def tune(pipeline, queries, judgments, ids, protocol):
    grid = protocol["grid"]
    configs = [dict(k1=k1, b=b) for k1, b in itertools.product(grid["k1"], grid["b"])]
    values = {("sparse", c["k1"], c["b"], 0): [] for c in configs}
    values.update({("hybrid", c["k1"], c["b"], k): [] for c in configs for k in grid["rrf_k"]})
    for number, qid in enumerate(ids, 1):
        dense, _ = pipeline.dense(queries[qid])
        for config in configs:
            sparse, _ = pipeline.sparse(queries[qid], config)
            values["sparse", config["k1"], config["b"], 0].append(
                score(pipeline.documents(sparse, qid), judgments[qid])["ndcg"]
            )
            for k in grid["rrf_k"]:
                hybrid, _ = pipeline.hybrid(sparse, dense, k)
                values["hybrid", config["k1"], config["b"], k].append(
                    score(pipeline.documents(hybrid, qid), judgments[qid])["ndcg"]
                )
        if number % 25 == 0:
            print(f"development: {number}/{len(ids)}", flush=True)
    means = {key: statistics.mean(value) for key, value in values.items()}
    winners = {}
    for mode in ("sparse", "hybrid"):
        winner = min((key for key in means if key[0] == mode), key=lambda key: (-means[key], key))
        winners[mode] = {"k1": winner[1], "b": winner[2], "rrf_k": winner[3] or 60}
    return {
        "selected": winners,
        "development_query_ids": ids,
        "grid_scores": [
            {"mode": key[0], "k1": key[1], "b": key[2], "rrf_k": key[3], "ndcg@10": means[key]}
            for key in sorted(means)
        ],
    }


def evaluate(pipeline, name, queries, judgments, ids, protocol, selection):
    configurations = {
        "default_sparse": protocol["defaults"],
        "default_dense": protocol["defaults"],
        "default_hybrid": protocol["defaults"],
        "tuned_sparse": selection["selected"]["sparse"],
        "tuned_hybrid": selection["selected"]["hybrid"],
    }
    outcomes = {key: [] for key in configurations}
    failures = {key: [] for key in configurations}
    # A declared warmup is excluded from measurement and uses no judgment.
    pipeline.sparse("retrieval", protocol["defaults"])
    pipeline.dense("retrieval")
    for number, qid in enumerate(ids, 1):
        # Run each configuration independently so latency includes its real work.
        for label, config in configurations.items():
            try:
                mode = label.split("_", 1)[1]
                elapsed = 0
                if mode in ("sparse", "hybrid"):
                    sparse, elapsed = pipeline.sparse(queries[qid], config)
                    hits = sparse
                if mode in ("dense", "hybrid"):
                    dense, duration = pipeline.dense(queries[qid])
                    elapsed += duration
                    hits = dense
                if mode == "hybrid":
                    hits, duration = pipeline.hybrid(sparse, dense, config["rrf_k"])
                    elapsed += duration
                ranking = pipeline.documents(hits, qid)
                outcomes[label].append(
                    {
                        "query_id": qid,
                        **score(ranking, judgments[qid]),
                        "elapsed_ms": elapsed,
                        "ranking": ranking,
                    }
                )
            except (ValueError, OSError) as error:
                failures[label].append({"query_id": qid, "error": type(error).__name__})
        if number % 25 == 0:
            print(f"{name} test: {number}/{len(ids)}", flush=True)
    reports = {}
    for label, rows in outcomes.items():
        times = [row["elapsed_ms"] for row in rows]
        reports[label] = {
            "schema_version": 1,
            "dataset_id": name,
            "split": "test",
            "cutoff": 10,
            "includes_drafts": False,
            "per_query": rows,
            "failures": failures[label],
            "missing_queries": [],
            "results_sha256": digest(canonical(rows)),
            "configuration": configurations[label],
            "metrics": {
                key: statistics.mean(row[key] for row in rows) if rows else None
                for key in ("ndcg", "recall", "mrr")
            },
            "latency_ms": {"p50": percentile(times, 0.5), "p95": percentile(times, 0.95)},
        }
    pairs = {}
    for left, right in (
        ("default_sparse", "default_dense"),
        ("default_sparse", "default_hybrid"),
        ("default_sparse", "tuned_sparse"),
        ("default_hybrid", "tuned_hybrid"),
    ):
        pairs[f"{left}_vs_{right}"] = compare(
            reports[left],
            reports[right],
            samples=protocol["bootstrap_samples"],
            seed=protocol["seed"],
        )
    return {"runs": reports, "paired_bootstrap": pairs}
