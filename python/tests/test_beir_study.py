import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from retrievec.evaluation.beir_reranker import CrossEncoder
from retrievec.evaluation.beir_study import freeze, latency_comparison, report_run


class StudyTests(unittest.TestCase):
    def test_freeze_rejects_changed_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "selection.json"
            freeze(path, {"weight": 0.5})
            freeze(path, {"weight": 0.5})
            with self.assertRaisesRegex(ValueError, "frozen artifact differs"):
                freeze(path, {"weight": 0.75})

    def test_query_accounting_and_paired_latency(self):
        with self.assertRaisesRegex(ValueError, "query accounting"):
            report_run("fixture", {}, [], [], ["q"])
        left = {
            "per_query": [{"query_id": "a", "elapsed_ms": 20}, {"query_id": "b", "elapsed_ms": 40}]
        }
        right = {
            "per_query": [{"query_id": "b", "elapsed_ms": 35}, {"query_id": "a", "elapsed_ms": 15}]
        }
        result = latency_comparison(left, right, 100, 1729)
        self.assertEqual(result["percentile_interval_95"], [-5, -5])
        self.assertEqual(result["paired_count"], 2)
        with self.assertRaises(ValueError):
            latency_comparison(left, {"per_query": []}, 100, 1729)

    def test_reranker_rejects_overflow_before_inference_and_preserves_title(self):
        encoder = CrossEncoder.__new__(CrossEncoder)
        encoder.config = {"max_tokens": 512, "batch_size": 16}
        encoder.tokenizer = Mock()
        encoder.tokenizer.encode_batch.return_value = [SimpleNamespace(ids=list(range(513)))]
        encoder.session = Mock()
        with self.assertRaisesRegex(ValueError, "no candidate truncated"):
            encoder.score("question", [{"title": "Title", "text": "Passage"}])
        encoder.tokenizer.encode_batch.assert_called_once_with([("question", "Title\n\nPassage")])
        encoder.session.run.assert_not_called()
