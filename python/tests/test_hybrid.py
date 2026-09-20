import unittest

from retrievallab.dense.hybrid import fuse


class FusionTests(unittest.TestCase):
    def test_deduplicate_accumulate_then_rank(self):
        def ranking(*ids):
            return [{"chunk_id": key} for key in ids]

        result = fuse([ranking("b", "b", "a"), ranking("a", "c")])
        self.assertEqual([v["chunk_id"] for v in result], ["a", "b", "c"])
        self.assertEqual(result[0]["rrf_score"], 1 / 62 + 1 / 61)
        self.assertEqual(fuse([[], []]), [])
        self.assertEqual([v["chunk_id"] for v in fuse([ranking("b"), ranking("a")])], ["a", "b"])
