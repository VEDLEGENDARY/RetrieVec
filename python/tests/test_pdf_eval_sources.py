import runpy
import tempfile
import unittest
from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest

FETCH = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "scripts/fetch_pdf_evaluation.py")
)["fetch"]


class PdfEvaluationSourceTests(unittest.TestCase):
    def test_existing_pdf_must_match_pinned_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = b"%PDF-1.7\nfixture"
            paper_id = "2024.acl-long.1"
            record = {
                "paper_id": paper_id,
                "path": paper_id + ".pdf",
                "source_url": f"https://aclanthology.org/{paper_id}/",
                "source_sha256": digest(source),
            }
            manifest = root / "manifest.json"
            manifest.write_bytes(canonical({"schema_version": 1, "sources": [record]}))
            output = root / "papers"
            output.mkdir()
            (output / record["path"]).write_bytes(source)
            self.assertEqual(FETCH(manifest, output), [])
            (output / record["path"]).write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "checksum differs"):
                FETCH(manifest, output)
            record["source_url"] = "https://example.org/file.pdf"
            manifest.write_bytes(canonical({"schema_version": 1, "sources": [record]}))
            with self.assertRaisesRegex(ValueError, "pinned ACL"):
                FETCH(manifest, output)
