"""Failures and exported reviews must preserve the evidence actually evaluated."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from retrievec.experiments.reranker import (
    CallableReranker,
    OnnxCrossEncoder,
    evaluate_baseline,
    evaluate_pool_sweep,
    pretrained_config,
    rerank,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from eval_answers import export_reviews, load_cases  # noqa: E402


class EvaluationIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.pool = {
            "query_id": "q1",
            "query": "How many participants?",
            "candidates": [{"chunk_id": "c1", "paper_id": "p1", "text": "12 people."}],
        }

    def test_model_failure_does_not_erase_successful_hybrid_baseline(self):
        def fail(pairs):
            raise RuntimeError("inference unavailable")

        model = CallableReranker(pretrained_config(), fail)
        report = evaluate_pool_sweep(
            [self.pool], {"q1": {"p1": 1}}, model, judgment_unit="paper_id"
        )
        result = report["sizes"]["50"]
        self.assertEqual(result["baseline"]["ndcg"]["mean"], 1)
        paired = result["paired_vs_plain_hybrid"]
        self.assertEqual(paired["left_failures"], 0)
        self.assertEqual(paired["right_failures"], 1)
        self.assertEqual(paired["metrics"]["ndcg"]["excluded_query_ids"], ["q1"])

    def test_unjudged_pool_is_not_quality_evidence(self):
        model = CallableReranker(pretrained_config(), lambda pairs: [1.0] * len(pairs))
        report = evaluate_baseline([self.pool], {}, model)
        self.assertFalse(report["quality_evidence"])

    def test_nonfinite_custom_model_scores_are_rejected_at_ranking_boundary(self):
        class InvalidModel:
            config = pretrained_config()

            def score(self, pairs):
                return [float("nan")]

        with self.assertRaisesRegex(ValueError, "scores"):
            rerank("question", self.pool["candidates"], InvalidModel(), top_k=1)

    def test_native_inference_failure_uses_recoverable_runtime_error(self):
        class NativeFailure(Exception):
            pass

        def fail(*args):
            raise NativeFailure("native runtime failure")

        model = OnnxCrossEncoder.__new__(OnnxCrossEncoder)
        model.config = pretrained_config()
        model.batch_size = 8
        model.tokenizer = SimpleNamespace(
            encode=lambda *args: SimpleNamespace(ids=[1], attention_mask=[1], type_ids=[0])
        )
        model.input_names = {"input_ids", "attention_mask"}
        model.session = SimpleNamespace(run=fail)
        with self.assertRaises(RuntimeError) as error:
            model.score([("question", "passage")])
        self.assertIsInstance(error.exception.__cause__, NativeFailure)

    def test_review_contains_actual_packed_evidence_and_failure(self):
        evidence = [{"evidence_id": "e1", "chunk_id": "c1", "text": "12 people."}]
        report = {
            "dataset_sha256": "a" * 64,
            "runs": [
                {
                    "provider_id": "local",
                    "cases": [
                        {
                            "question_id": "q1",
                            "evidence": evidence,
                            "failure": "RuntimeError: generation unavailable",
                        }
                    ],
                }
            ],
        }
        row = export_reviews(report, [{"id": "q1", "question": "How many?"}])["rows"][0]
        self.assertEqual(row["evidence"], evidence)
        self.assertEqual(row["failure"], "RuntimeError: generation unavailable")
        self.assertIsNone(row["human_claim_support"])

    def test_empty_or_malformed_answer_sets_fail_before_provider_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            for questions in ([], [None], [{"id": "q", "question": "Q", "empty": "false"}]):
                with self.subTest(questions=questions):
                    path.write_text(json.dumps({"schema_version": 1, "questions": questions}))
                    with self.assertRaises(ValueError):
                        load_cases(path)


if __name__ == "__main__":
    unittest.main()
