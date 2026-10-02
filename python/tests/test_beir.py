import math
import tempfile
import unittest
from pathlib import Path

from retrievec.evaluation.beir_data import qrels
from retrievec.evaluation.beir_eval import score
from retrievec.evaluation.beir_runtime import Pipeline


class BeirTests(unittest.TestCase):
    def test_binary_labels_and_cutoffs(self):
        ranking = ["unjudged", "a"] + [f"x{i}" for i in range(98)] + ["b"]
        result = score(ranking, {"a": 1, "b": 1, "negative": 0})
        self.assertAlmostEqual(result["ndcg"], (1 / math.log2(3)) / (1 + 1 / math.log2(3)))
        self.assertEqual(result["mrr"], 0.5)
        self.assertEqual(result["recall"], 0.5)
        self.assertEqual(score([], {"a": 1})["ndcg"], 0)
        with self.assertRaises(ValueError):
            score(["a", "a"], {"a": 1})
        with self.assertRaises(ValueError):
            score(["a"], {"a": 0})

    def test_duplicate_and_nonbinary_judgments_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "qrels.tsv"
            header = "query-id\tcorpus-id\tscore\n"
            path.write_text(header + "q\ta\t1\nq\tb\t0\n", encoding="utf-8")
            self.assertEqual(qrels(path), {"q": {"a": 1, "b": 0}})
            for contents in ("q\ta\t1\nq\ta\t1\n", "q\ta\t2\n"):
                path.write_text(header + contents, encoding="utf-8")
                with self.assertRaises(ValueError):
                    qrels(path)

    def test_document_collapse_keeps_first_rank_and_excludes_self(self):
        pipeline = object.__new__(Pipeline)
        pipeline.papers = {"c1": "query", "c2": "a", "c3": "a", "c4": "b"}
        hits = [{"chunk_id": key} for key in pipeline.papers]
        self.assertEqual(pipeline.documents(hits, "query"), ["a", "b"])
