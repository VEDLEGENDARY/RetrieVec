"""Paired query bootstrap for existing, provenance-bound evaluation reports."""

import math
import random

from retrievec.evaluation.load import percentile


def compare(left, right, *, samples=5000, seed=1729):
    if type(samples) is not int or not 100 <= samples <= 20000:
        raise ValueError("bootstrap samples must be between 100 and 20000")
    for field in ("schema_version", "dataset_id", "split", "cutoff", "includes_drafts"):
        if field not in left or left[field] != right.get(field):
            raise ValueError("incompatible evaluation reports: " + field)

    def index(report):
        rows = {}
        for row in report["per_query"]:
            key = row["query_id"]
            if key in rows:
                raise ValueError("duplicate query metric")
            rows[key] = row
        failed = [row["query_id"] for row in report["failures"]]
        missing = report["missing_queries"]
        all_ids = [*rows, *failed, *missing]
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("query occurs in multiple outcome groups")
        return rows, set(all_ids)

    a, universe_a = index(left)
    b, universe_b = index(right)
    if universe_a != universe_b or not universe_a:
        raise ValueError("comparisons require identical nonempty query sets")
    result = {}
    for metric in ("ndcg", "mrr", "recall", "coverage"):
        pairs, excluded = [], []
        for key in sorted(universe_a):
            av, bv = a.get(key, {}).get(metric), b.get(key, {}).get(metric)
            for value in (av, bv):
                if value is not None and (
                    type(value) not in (float, int)
                    or not math.isfinite(value)
                    or not 0 <= value <= 1
                ):
                    raise ValueError("invalid bounded retrieval metric")
            if av is None or bv is None:
                excluded.append(key)
            else:
                pairs.append(bv - av)
        rng = random.Random(seed)
        draws = (
            [sum(rng.choices(pairs, k=len(pairs))) / len(pairs) for _ in range(samples)]
            if pairs
            else []
        )
        result[metric] = {
            "paired_count": len(pairs),
            "excluded_count": len(excluded),
            "excluded_query_ids": excluded,
            "mean_delta_right_minus_left": sum(pairs) / len(pairs) if pairs else None,
            "percentile_interval_95": [percentile(draws, 0.025), percentile(draws, 0.975)],
        }
    return {
        "schema_version": 1,
        "dataset_id": left["dataset_id"],
        "split": left["split"],
        "cutoff": left["cutoff"],
        "includes_drafts": left["includes_drafts"],
        "query_count": len(universe_a),
        "left_results_sha256": left["results_sha256"],
        "right_results_sha256": right["results_sha256"],
        "left_failures": len(left["failures"]),
        "right_failures": len(right["failures"]),
        "left_missing": len(left["missing_queries"]),
        "right_missing": len(right["missing_queries"]),
        "samples": samples,
        "seed": seed,
        "metrics": result,
        "interpretation": "Query-paired descriptive bootstrap; failed, missing and undefined "
        "queries are counted separately, never silently scored as success. Small or repeatedly "
        "inspected sets do not establish general superiority. Draft labels are not human review.",
    }
