import asyncio
import copy
import unittest
from pathlib import Path
from types import SimpleNamespace

import httpx
from retrievec.corpus.snapshot import canonical, digest
from retrievec.evaluation.answer_pipeline import evaluate
from retrievec.evaluation.answer_quality import (
    export_review,
    import_review,
    load_dataset,
    summarize,
)


def report_fixture():
    return {
        "dataset_sha256": "fixed",
        "split": "test",
        "providers": {"local": {}},
        "cases": [
            {
                "case_id": "local/q1",
                "provider": "local",
                "question": "A question",
                "question_kind": "answerable",
                "state": "completed",
                "elapsed_ms": 100,
                "result": {
                    "answer": {
                        "status": "answered",
                        "claims": [{"id": "c1", "text": "Claim", "evidence_ids": ["e1"]}],
                        "comparisons": [{"evidence_ids": ["e2"]}],
                    },
                    "evidence": [{"evidence_id": "e1", "text": "Evidence"}],
                },
                "human_review": None,
                "llm_judge": None,
            }
        ],
    }


class AnswerQualityTests(unittest.TestCase):
    def test_resume_preserves_failed_outcomes_and_rejects_changed_identity(self):
        path = Path(__file__).resolve().parents[2] / "datasets/answer_quality/questions-v1.json"
        dataset, sources = load_dataset(path)
        provider = {"name": "local", "model": "Qwen2.5-1.5B", "cloud": False, "consented": True}
        args = SimpleNamespace(
            origin="http://127.0.0.1:8000",
            dataset=path,
            collection="fixed",
            snapshot="pinned",
            providers=["local"],
            split="test",
            timeout=30,
        )
        corpus = (
            {"collection_id": "fixed"},
            [{"paper_id": key, "source_sha256": value} for key, value in sources.items()],
            [],
        )
        calls = []

        def respond(request):
            calls.append(request.method)
            if request.url.path.endswith("/me"):
                return httpx.Response(200, json={})
            if request.url.path.endswith("/collections"):
                return httpx.Response(
                    200, json=[{"collection_id": "fixed", "active_snapshot": "pinned"}]
                )
            return httpx.Response(200, json=[provider])

        resume = {
            "schema_version": 1,
            "dataset_sha256": digest(canonical(dataset)),
            "split": "test",
            "snapshot_id": "pinned",
            "collection_id": "fixed",
            "providers": {"local": provider},
            "cases": [
                {
                    "case_id": "local/" + q["id"],
                    "provider": "local",
                    "state": "failed",
                    "error_code": "invalid_answer",
                    "human_review": None,
                    "llm_judge": None,
                }
                for q in dataset["questions"]
                if q["split"] == "test"
            ],
        }

        def run(value):
            return asyncio.run(
                evaluate(
                    args,
                    {"session_cookie": "private", "csrf_token": "private"},
                    corpus,
                    transport=httpx.MockTransport(respond),
                    resume=value,
                )
            )

        result = run(resume)
        self.assertTrue(result["complete"])
        self.assertFalse(result["all_runs_completed"])
        self.assertEqual(result["cases"], resume["cases"])
        self.assertTrue(all(method == "GET" for method in calls))
        changed = copy.deepcopy(resume)
        changed["providers"]["local"]["model"] = "different"
        with self.assertRaisesRegex(ValueError, "providers"):
            run(changed)
        duplicate = copy.deepcopy(resume)
        duplicate["cases"].append(duplicate["cases"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            run(duplicate)

    def test_cloud_consent_and_active_snapshot_are_checked_before_mutations(self):
        root = Path(__file__).resolve().parents[2]
        path = root / "datasets/answer_quality/questions-v1.json"
        _, sources = load_dataset(path)
        corpus = (
            {"collection_id": "fixed"},
            [{"paper_id": key, "source_sha256": value} for key, value in sources.items()],
            [],
        )
        args = SimpleNamespace(
            origin="http://127.0.0.1:8000",
            dataset=path,
            collection="fixed",
            snapshot="pinned",
            providers=["local", "stronger"],
            split="test",
            timeout=30,
        )
        calls = []

        def respond(request):
            calls.append((request.method, request.url.path))
            if request.url.path.endswith("/me"):
                return httpx.Response(200, json={"principal_id": "owner"})
            if request.url.path.endswith("/collections"):
                return httpx.Response(
                    200, json=[{"collection_id": "fixed", "active_snapshot": "pinned"}]
                )
            return httpx.Response(
                200,
                json=[
                    {"name": "local", "model": "Qwen2.5-1.5B", "cloud": False, "consented": True},
                    {"name": "stronger", "cloud": True, "consented": False},
                ],
            )

        with self.assertRaisesRegex(ValueError, "consent"):
            asyncio.run(
                evaluate(
                    args,
                    {"session_cookie": "private", "csrf_token": "private"},
                    corpus,
                    transport=httpx.MockTransport(respond),
                )
            )
        self.assertTrue(all(method == "GET" for method, _ in calls))
        args.snapshot = "other"
        with self.assertRaisesRegex(ValueError, "snapshot"):
            asyncio.run(
                evaluate(
                    args,
                    {"session_cookie": "private", "csrf_token": "private"},
                    corpus,
                    transport=httpx.MockTransport(respond),
                )
            )

    def test_fixed_dataset_has_isolated_splits(self):
        root = Path(__file__).resolve().parents[2]
        dataset, sources = load_dataset(root / "datasets/answer_quality/questions-v1.json")
        self.assertEqual(len(sources), 24)
        self.assertEqual(sum(q["split"] == "test" for q in dataset["questions"]), 60)
        self.assertTrue(all(q["reviewer"] is None for q in dataset["questions"]))

    def test_export_does_not_invent_review_or_semantic_scores(self):
        report = report_fixture()
        packet = export_review(report)
        self.assertEqual(len(packet["cases"][0]["citations"]), 2)
        self.assertIsNone(packet["cases"][0]["faithfulness"])
        import_review(report, packet)
        result = summarize(report)
        self.assertIsNone(result["summary"]["local"]["human"]["citation_precision"])
        self.assertIsNone(result["summary"]["local"]["ttft_worker_ms"]["p50"])
        self.assertIsNone(result["judge_vs_human"]["citation_support_agreement"])

    def test_review_rejects_changed_evidence_and_requires_full_assessment(self):
        report = report_fixture()
        packet = export_review(report)
        row = packet["cases"][0]
        row.update(
            reviewed=True,
            reviewer="Reviewer",
            reviewed_at="2026-10-05T12:00:00Z",
            faithfulness=0.5,
            abstention_correct=True,
        )
        for citation in row["citations"]:
            citation.update(supported=False, rationale="Passage does not support the claim")
        tampered = copy.deepcopy(report)
        tampered["cases"][0]["result"]["evidence"][0]["text"] = "Changed"
        with self.assertRaisesRegex(ValueError, "changed"):
            import_review(tampered, packet)
        import_review(report, packet)
        self.assertEqual(summarize(report)["summary"]["local"]["human"]["citation_precision"], 0)
        row["citations"].pop()
        with self.assertRaisesRegex(ValueError, "every"):
            import_review(report, packet)
