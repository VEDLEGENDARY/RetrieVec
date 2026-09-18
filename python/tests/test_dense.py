import math
import unittest

import numpy as np

from retrievallab.dense.model import FixtureModel, normalize
from retrievallab.dense.search import exact_search


class DenseTests(unittest.TestCase):
    def test_independent_cosines_and_ties(self):
        vectors = normalize(np.array([[1, 0], [1, 1], [0, 1], [1, 0]], dtype=np.float32))
        hits = exact_search(vectors, ["b", "c", "d", "a"], [1, 0], 4, block_size=1)
        self.assertEqual([h["chunk_id"] for h in hits], ["a", "b", "c", "d"])
        self.assertAlmostEqual(hits[2]["cosine_score"], 1 / math.sqrt(2), places=6)
        self.assertEqual(hits[-1]["cosine_score"], 0)
        self.assertEqual(hits, exact_search(vectors, ["b", "c", "d", "a"], [1, 0], 4, block_size=3))

    def test_invalid_vectors(self):
        for value in ([[0, 0]], [[math.nan, 0]], [[math.inf, 1]]):
            with self.assertRaises(ValueError):
                normalize(np.array(value))
        with self.assertRaises(ValueError):
            exact_search(np.array([[1, 0]]), ["a"], [1], 1)
        self.assertTrue(np.array_equal(FixtureModel().encode(["red blue"]), FixtureModel().encode(["red blue"])))
