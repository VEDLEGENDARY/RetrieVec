import json
import runpy
import unittest
from pathlib import Path

TABLES = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/render_beir_report.py"))[
    "tables"
]
SUMMARY = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "scripts/render_beir_report.py")
)["readme_summary"]


class BeirReportingTests(unittest.TestCase):
    def test_published_tables_match_complete_json(self):
        root = Path(__file__).resolve().parents[2]
        report = json.loads((root / "docs/results/benchmark-2026-10-01.json").read_bytes())
        expected = TABLES(report)
        self.assertIn(expected, (root / "BENCHMARKS.md").read_text(encoding="utf-8"))
        current = json.loads((root / "docs/results/benchmark-2026-10-05-phase3.json").read_bytes())
        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertIn(SUMMARY(current), readme)
        self.assertLess(len(readme.splitlines()), 250)
        self.assertIn("differs from the product's default PDF upload chunking", readme)

    def test_partial_and_subset_results_cannot_be_published_as_quality(self):
        for report in (
            {"complete": False},
            {"complete": True, "quality_evidence": False},
            {"complete": True, "quality_evidence": True, "kind": "smoke-subset"},
            {
                "complete": True,
                "quality_evidence": True,
                "kind": "full-beir",
                "datasets": {"scifact": {}},
            },
        ):
            with self.subTest(report=report), self.assertRaises(ValueError):
                TABLES(report)

    def test_failed_query_accounting_rejects_false_complete_flag(self):
        dataset = {
            "query_count": 1,
            "runs": {
                "default_sparse": {
                    "failures": [{"query_id": "synthetic"}],
                    "per_query": [],
                }
            },
        }
        report = {
            "complete": True,
            "quality_evidence": True,
            "kind": "full-beir",
            "datasets": {"scifact": dataset, "scidocs": dataset},
        }
        with self.assertRaises(ValueError):
            TABLES(report)
