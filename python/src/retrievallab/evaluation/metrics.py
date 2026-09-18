"""Replayable ranking metrics; missing judgments never become stored negatives."""

import math


def metrics(ranking: list[str], judgments: dict[str, int], k: int = 10) -> dict:
    if type(k) is not int or k < 1 or len(set(ranking)) != len(ranking):
        raise ValueError("invalid cutoff or duplicate ranking IDs")
    if any(type(grade) is not int or not 0 <= grade <= 3 for grade in judgments.values()):
        raise ValueError("invalid relevance grade")
    hits = ranking[:k]
    positives = {key for key, grade in judgments.items() if grade >= 2}
    ideal = sorted(judgments.values(), reverse=True)[:k]
    ideal_dcg = sum((2**grade - 1) / math.log2(rank + 2) for rank, grade in enumerate(ideal))
    dcg = sum((2**judgments.get(key, 0) - 1) / math.log2(rank + 2) for rank, key in enumerate(hits))
    return {"ndcg": dcg / ideal_dcg if ideal_dcg else None, "mrr": next((1 / rank for rank, key in enumerate(hits, 1) if key in positives), 0) if positives else None, "recall": len(set(hits) & positives) / len(positives) if positives else None, "coverage": sum(key in judgments for key in hits) / len(hits) if hits else None, "empty": not hits, "known_positives": len(positives), "returned": len(hits)}


def aggregate(rows: list[dict]) -> dict:
    result = {}
    for key in ("ndcg", "mrr", "recall", "coverage"):
        values = [row[key] for row in rows if row[key] is not None]
        result[key] = {"mean": sum(values) / len(values) if values else None, "defined_queries": len(values), "undefined_queries": len(rows) - len(values)}
    result["empty_result_rate"] = sum(row["empty"] for row in rows) / len(rows) if rows else None
    return result
