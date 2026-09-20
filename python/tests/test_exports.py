import csv
import io
import json
import unittest

from retrievec.app.exports import bibtex, cell, markdown, render


class ExportTests(unittest.TestCase):
    def test_hostile_fields_remain_inert(self):
        for text in ("=CMD()", " +CMD()", "@SUM(A1)", "\tformula"):
            self.assertTrue(cell(text).startswith("'"))
        self.assertEqual(cell("ordinary"), "ordinary")
        self.assertIn(r"\}", bibtex("author} evil{"))
        self.assertIn(r"\<", markdown("<script>bad</script>"))
        self.assertIn(r"\[", markdown("[link](javascript:bad)"))

    def test_exports_use_saved_provenance_and_known_metadata_only(self):
        run = {
            "run_id": "run",
            "snapshot_id": "rs_saved",
            "original_question": "Question",
            "effective_query": "Standalone",
            "parent_run": None,
            "created_at": "today",
            "configuration": {"generation": {"model": "local", "revision": "pinned"}},
            "result": {
                "answer": {
                    "status": "insufficient_evidence",
                    "claims": [],
                    "comparisons": [],
                    "limitations": ["Unknown"],
                },
                "evidence": [
                    {
                        "evidence_id": "e_1",
                        "paper_id": "p",
                        "paper_version_id": "pv_a",
                        "title": "=Hostile title",
                        "text": "Exact passage",
                        "authors": [],
                    }
                ],
            },
        }
        text, _, _ = render(run, "json")
        self.assertEqual(json.loads(text)["snapshot_id"], "rs_saved")
        text, _, _ = render(run, "bibtex")
        self.assertNotIn("doi", text)
        text, _, _ = render(run, "csv")
        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(rows[1][3], "'=Hostile title")
        text, _, _ = render(run, "markdown")
        self.assertIn("rs_saved", text)
