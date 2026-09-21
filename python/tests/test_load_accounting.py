import unittest

from retrievec.evaluation.load import percentile, summarize


class LoadAccountingTests(unittest.TestCase):
    def test_timeouts_remain_in_denominator_and_latency_distribution(self):
        report = summarize(
            [
                {"outcome": "completed", "elapsed_ms": 10},
                {"outcome": "failed", "elapsed_ms": 1000, "error_code": "timeout"},
                {"outcome": "completed", "elapsed_ms": 20},
            ]
        )
        self.assertEqual(report["request_count"], 3)
        self.assertEqual(report["successes"], 2)
        self.assertEqual(report["errors"], {"timeout": 1})
        self.assertGreater(report["all_outcomes_ms"]["p95"], 900)
        self.assertEqual(report["successful_ms"]["p50"], 15)
        self.assertIsNone(percentile([], 0.95))
