import unittest

from retrievec.evaluation.paired import compare


def report(score):
    return {
        "schema_version": 1,
        "dataset_id": "fixture",
        "split": "held_out",
        "cutoff": 10,
        "includes_drafts": False,
        "results_sha256": "fixture",
        "per_query": [
            {"query_id": "q1", "ndcg": score, "mrr": score, "recall": score, "coverage": 1}
        ],
        "failures": [{"query_id": "q2", "error": "timeout"}],
        "missing_queries": ["q3"],
    }


class PairedEvaluationTests(unittest.TestCase):
    def test_failures_remain_visible_and_sampling_is_reproducible(self):
        result = compare(report(0.25), report(0.75), samples=100)
        self.assertEqual(result, compare(report(0.25), report(0.75), samples=100))
        self.assertEqual(result["query_count"], 3)
        self.assertEqual(result["metrics"]["ndcg"]["paired_count"], 1)
        self.assertEqual(result["metrics"]["ndcg"]["excluded_count"], 2)
        self.assertEqual(result["metrics"]["ndcg"]["percentile_interval_95"], [0.5, 0.5])

    def test_incompatible_queries_and_judgments_are_rejected(self):
        left, right = report(0.5), report(0.5)
        right["includes_drafts"] = True
        with self.assertRaises(ValueError):
            compare(left, right)
        right = report(0.5)
        right["missing_queries"] = []
        with self.assertRaises(ValueError):
            compare(left, right)
