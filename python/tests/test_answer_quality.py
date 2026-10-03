"""Regressions for answer evidence signals and opt-in reranker comparisons."""

import hashlib
import json
import unittest
from pathlib import Path

from pydantic import ValidationError
from retrievec.app.schemas import SearchInput
from retrievec.evaluation.answer_signals import automatic_signals
from retrievec.experiments.reranker import (
    CallableReranker,
    evaluate_pool_sweep,
    pretrained_config,
)


class AnswerSignalsTest(unittest.TestCase):
    def test_invalid_number_is_not_scored_as_supported(self):
        evidence = [{"evidence_id": "e_1", "text": "The trial enrolled 12 people."}]
        raw = json.dumps(
            {
                "status": "answered",
                "claims": [
                    {
                        "id": "c1",
                        "text": "The trial enrolled 99 people.",
                        "evidence_ids": ["e_1"],
                        "support_status": "structurally_valid",
                        "quotes": [{"evidence_id": "e_1", "text": evidence[0]["text"]}],
                    }
                ],
                "comparisons": [],
                "limitations": [],
            }
        )
        result = automatic_signals(raw, evidence)
        self.assertFalse(result["structurally_valid"])
        self.assertIn("unsupported numerical literal", result["failure"])

    def test_valid_abstention_keeps_claim_metrics_undefined(self):
        raw = json.dumps(
            {
                "status": "insufficient_evidence",
                "claims": [],
                "comparisons": [],
                "limitations": ["No relevant evidence was retrieved"],
            }
        )
        result = automatic_signals(raw, [], expected_unanswerable=True)
        self.assertTrue(result["structurally_valid"])
        self.assertTrue(result["abstention_correct"])
        self.assertIsNone(result["citation_precision"])
        self.assertIsNone(result["entailment_proxy"])


class RerankerSweepTest(unittest.TestCase):
    def test_pending_pdf_questions_cannot_become_reviewed_answer_set(self):
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
        from build_reviewed_answer_set import build

        passage = "The paper reports 12 participants."
        candidate = {
            "candidate_id": "pq_1",
            "chunk_id": "c1",
            "paper_id": "p1",
            "paper_title": "Paper",
            "page_range": [1, 1],
            "source_sha256": "s" * 64,
            "text_sha256": hashlib.sha256(passage.encode()).hexdigest(),
            "passage": passage,
            "question": "How many participants?",
            "expected_answer": "12",
            "reviewer": None,
            "review_rationale": "",
            "review_status": "pending",
            "question_type": "numeric",
        }
        packet = {
            "schema_version": 1,
            "kind": "pdf-passage-review-packet",
            "corpus_snapshot_id": "ss_1",
            "manifest_sha256": "m" * 64,
            "candidates": [candidate],
        }
        with self.assertRaisesRegex(ValueError, "only 0 reviewed"):
            build(packet, min_questions=1)

    def test_runtime_rerank_is_opt_in_and_hybrid_only(self):
        self.assertFalse(SearchInput(collection_id="c", query="question").rerank)
        self.assertTrue(
            SearchInput(collection_id="c", query="question", retrieval="hybrid", rerank=True).rerank
        )
        with self.assertRaises(ValidationError):
            SearchInput(collection_id="c", query="question", retrieval="sparse", rerank=True)

    def test_paper_level_reranking_preserves_candidate_recall(self):
        model = CallableReranker(
            pretrained_config(),
            lambda pairs: [2.0 if "relevant" in passage else 0.0 for _, passage in pairs],
        )
        pools = [
            {
                "query_id": "q1",
                "query": "question",
                "candidates": [
                    {"chunk_id": "c1", "paper_id": "p1", "text": "unrelated"},
                    {"chunk_id": "c2", "paper_id": "p2", "text": "relevant"},
                ],
            }
        ]
        report = evaluate_pool_sweep(pools, {"q1": {"p2": 1}}, model, judgment_unit="paper_id")
        self.assertEqual(report["sizes"]["20"]["candidate_recall"], 1.0)
        self.assertGreater(
            report["sizes"]["20"]["reranked"]["ndcg"]["mean"],
            report["sizes"]["20"]["baseline"]["ndcg"]["mean"],
        )
        self.assertFalse(report["default_changed"])
        paired = report["sizes"]["20"]["paired_vs_plain_hybrid"]["metrics"]["ndcg"]
        self.assertEqual(paired["paired_count"], 1)
        self.assertGreater(paired["percentile_interval_95"][0], 0)
        self.assertAlmostEqual(
            paired["mean_delta_right_minus_left"],
            report["sizes"]["20"]["reranked"]["ndcg"]["mean"]
            - report["sizes"]["20"]["baseline"]["ndcg"]["mean"],
        )

    def test_paper_level_metric_deduplicates_before_top_ten(self):
        model = CallableReranker(
            pretrained_config(),
            lambda pairs: [2.0 if passage == "duplicate" else 1.0 for _, passage in pairs],
        )
        candidates = [
            {"chunk_id": f"c{index}", "paper_id": "p1", "text": "duplicate"} for index in range(11)
        ] + [{"chunk_id": "relevant", "paper_id": "p2", "text": "support"}]
        report = evaluate_pool_sweep(
            [{"query_id": "q", "query": "question", "candidates": candidates}],
            {"q": {"p2": 1}},
            model,
            judgment_unit="paper_id",
        )
        self.assertGreater(report["sizes"]["20"]["reranked"]["ndcg"]["mean"], 0)

    def test_review_packet_source_keeps_blank_human_labels(self):
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
        from eval_answers import export_reviews

        report = {
            "dataset_sha256": "a" * 64,
            "runs": [
                {
                    "provider_id": "provider-v1",
                    "cases": [{"question_id": "q1", "answer": "{}", "automatic": {}}],
                }
            ],
        }
        packet = export_reviews(report, [{"id": "q1", "question": "What?"}])
        self.assertIsNone(packet["rows"][0]["human_claim_support"])
        self.assertIsNone(packet["rows"][0]["reviewer"])


if __name__ == "__main__":
    unittest.main()
