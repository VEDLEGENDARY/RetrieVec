import unittest

from retrievec.dense.hybrid import fuse
from retrievec.evaluation.beir_variants import normalized_score, weighted_rrf


class FusionVariantTests(unittest.TestCase):
    def test_equal_weights_preserve_production_rrf_rank_and_tie_order(self):
        sparse = [{"chunk_id": key} for key in ("c", "c", "a", "b")]
        dense = [{"chunk_id": key} for key in ("a", "d", "b")]
        expected = fuse([sparse, dense])
        actual = weighted_rrf(sparse, dense, 0.5)
        self.assertEqual([r["chunk_id"] for r in actual], [r["chunk_id"] for r in expected])
        for left, right in zip(actual, expected, strict=True):
            self.assertEqual(left["fusion_score"] * 2, right["rrf_score"])

    def test_normalized_scores_missing_negative_and_constant_legs(self):
        sparse = [{"chunk_id": "a", "score": 10.0}, {"chunk_id": "b", "score": 5.0}]
        dense = [{"chunk_id": "b", "cosine_score": -0.1}, {"chunk_id": "c", "cosine_score": -0.5}]
        result = normalized_score(sparse, dense, 0.5)
        self.assertEqual(
            [(r["chunk_id"], r["fusion_score"]) for r in result],
            [("a", 0.5), ("b", 0.5), ("c", 0.0)],
        )
        self.assertEqual(normalized_score(sparse[:1], [], 0.25)[0]["fusion_score"], 0.25)
        self.assertEqual(normalized_score([], [], 0.5), [])
        with self.assertRaises(ValueError):
            normalized_score([{"chunk_id": "a", "score": float("nan")}], [], 0.5)
        for weight in (-1, 2, float("nan"), True):
            with self.assertRaises(ValueError):
                weighted_rrf([], [], weight)
