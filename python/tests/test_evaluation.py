import math
import unittest

from retrievec.evaluation.metrics import metrics


class MetricTests(unittest.TestCase):
    def test_hand_computed_metrics(self):
        result = metrics(["b", "x", "a"], {"a": 3, "b": 2, "c": 1}, k=3)
        expected = (3 + 7 / 2) / (7 + 3 / math.log2(3) + 1 / 2)
        self.assertAlmostEqual(result["ndcg"], expected)
        self.assertEqual(result["mrr"], 1)
        self.assertEqual(result["recall"], 1)
        self.assertEqual(result["coverage"], 2 / 3)

    def test_empty_and_no_positive(self):
        self.assertIsNone(metrics([], {})["recall"])
        self.assertIsNone(metrics([], {})["ndcg"])
        self.assertEqual(metrics([], {"a": 3})["recall"], 0)
        self.assertIsNone(metrics([], {"a": 3})["coverage"])
        with self.assertRaises(ValueError):
            metrics(["a", "a"], {"a": 3})
