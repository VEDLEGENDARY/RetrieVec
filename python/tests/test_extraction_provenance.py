import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from retrievec.app.uploads import job_view
from retrievec.registry.extraction_provenance import extraction_provenance


class ExtractionProvenanceTests(unittest.TestCase):
    def test_known_text_extractors_report_the_retained_revision_without_ocr(self):
        papers = [
            {"source_sha256": "a" * 64, "extraction_version": "utf8-text-v1"},
            {"source_sha256": "b" * 64, "extraction_version": "pypdf-6.10.0-plain-v1"},
            {"source_sha256": "c" * 64, "extraction_version": "unknown-adapter-v1"},
        ]
        values = extraction_provenance(Path("unused"), papers)
        self.assertEqual(values["a" * 64]["extractors"][0]["name"], "UTF-8 text reader")
        self.assertEqual(values["b" * 64]["extractors"], [{"name": "pypdf", "revision": "6.10.0"}])
        self.assertIs(values["b" * 64]["ocr_used"], False)
        self.assertIsNone(values["c" * 64]["ocr_used"])

    def test_typed_evidence_reports_actual_ocr_and_checks_the_source_identity(self):
        paper = {
            "source_sha256": "a" * 64,
            "extraction_version": "typed-evidence-v1-eb_" + "b" * 64,
        }
        item = SimpleNamespace(
            extractor="local-ocr", revision="retained-revision", derivation="ocr"
        )
        with patch(
            "retrievec.extraction.store.EvidenceStore.bundle",
            return_value=({"source_sha256": "a" * 64}, [item]),
        ):
            value = extraction_provenance(Path("unused"), [paper])["a" * 64]
        self.assertIs(value["ocr_used"], True)
        self.assertEqual(
            value["extractors"], [{"name": "local-ocr", "revision": "retained-revision"}]
        )
        with patch(
            "retrievec.extraction.store.EvidenceStore.bundle",
            return_value=({"source_sha256": "c" * 64}, [item]),
        ):
            with self.assertRaisesRegex(ValueError, "source differs"):
                extraction_provenance(Path("unused"), [paper])

    def test_job_view_only_exposes_the_jobs_files_and_labels_batch_scoped_stages(self):
        profile = {"source_sha256": "a" * 64, "extractors": [], "ocr_used": False}
        job = {
            "job_id": "job",
            "collection_id": "collection",
            "state": "succeeded",
            "stage": "activate",
            "progress": {"extraction": {"a" * 64: profile, "b" * 64: {"private": "other file"}}},
            "error_code": None,
            "output_snapshot": "snapshot",
        }
        source = {
            "source_id": "source",
            "display_name": "paper.txt",
            "size_bytes": 12,
            "media_type": "text/plain",
            "source_hash": "a" * 64,
        }
        value = job_view(job, [source])
        self.assertNotIn("extraction", value["progress"])
        self.assertEqual(len(value["progress"]["files"]), 1)
        self.assertEqual(value["progress"]["files"][0]["stage_scope"], "batch")
        self.assertEqual(value["progress"]["files"][0]["provenance"], profile)
        self.assertIn("extraction", job["progress"])
        job["state"] = "running"
        self.assertIsNone(job_view(job, [source])["progress"]["files"][0]["provenance"])
