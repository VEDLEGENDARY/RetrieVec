import math
import unittest

import numpy as np
from retrievec.dense.model import FixtureModel, normalize
from retrievec.dense.search import exact_search


class DenseTests(unittest.TestCase):
    def test_wordpiece_overflow_rejects_before_inference(self):
        from types import SimpleNamespace
        from unittest.mock import Mock

        from retrievec.dense.model import MiniLM

        model = MiniLM.__new__(MiniLM)
        model.tokenizer = Mock()
        model.tokenizer.encode_batch.return_value = [SimpleNamespace(ids=list(range(257)))]
        model.session = Mock()
        with self.assertRaisesRegex(ValueError, "exceeds 256 wordpieces"):
            model.encode(["scientific terms"])
        model.session.run.assert_not_called()

    def test_partition_matches_full_sort_at_tied_cutoff(self):
        rng = np.random.default_rng(19)
        vectors = normalize(rng.integers(-2, 3, (257, 7)).astype(np.float32) + 0.1)
        vectors[80:140] = vectors[0]
        ids = [f"chunk-{256 - i:04}" for i in range(len(vectors))]
        query = vectors[0]
        for block_size in (1, 31, 257):
            scores = np.concatenate(
                [vectors[i : i + block_size] @ query for i in range(0, len(vectors), block_size)]
            )
            reference = sorted(zip(scores, ids, strict=True), key=lambda item: (-item[0], item[1]))
            for limit in (1, 17, 100, 300):
                with self.subTest(block=block_size, limit=limit):
                    hits = exact_search(vectors, ids, query, limit, block_size)
                    self.assertEqual(
                        [h["chunk_id"] for h in hits], [key for _, key in reference[:limit]]
                    )

    def test_empty_collection_snapshot(self):
        import os
        import tempfile
        from pathlib import Path

        from retrievec.corpus.snapshot import publish_snapshot
        from retrievec.registry.artifacts import Store

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = publish_snapshot(root / "corpora", [], [], "empty", {})
            snapshot = Store(root).build(Path(os.environ["RETRIEVEC_ENGINE"]), corpus)
            self.assertEqual(Store(root).manifest(snapshot)["segments"], [])
        self.assertEqual(exact_search(np.empty((0, 2)), [], [1, 0]), [])

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
        self.assertTrue(
            np.array_equal(FixtureModel().encode(["red blue"]), FixtureModel().encode(["red blue"]))
        )
