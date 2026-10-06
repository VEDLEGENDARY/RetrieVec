import importlib.util
import tempfile
import unittest
from pathlib import Path

from retrievec.corpus.importer import import_manifest
from retrievec.corpus.snapshot import canonical, digest

spec = importlib.util.spec_from_file_location(
    "import_audit", Path(__file__).resolve().parents[2] / "scripts/audit_import.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ImportAuditTests(unittest.TestCase):
    def test_audit_preserves_valid_source_and_rejects_root_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            sources.mkdir()
            raw = b"Retained evidence from a bounded local source."
            (sources / "paper.txt").write_bytes(raw)
            outside = root / "outside.txt"
            outside.write_bytes(raw)
            record = {
                "paper_id": "paper",
                "title": "Paper",
                "authors": [],
                "path": "paper.txt",
                "source_url": None,
                "source_sha256": digest(raw),
                "license_note": "synthetic regression fixture",
            }
            manifest = root / "manifest.json"
            manifest.write_bytes(canonical({"schema_version": 1, "sources": [record]}))
            snapshot = import_manifest(manifest, sources, root / "store", "test", 256)
            self.assertEqual(module.audit(snapshot, manifest, sources)["papers"][0]["chunks"], 1)
            for path in ("../outside.txt", str(outside.resolve())):
                with self.subTest(path=path):
                    manifest.write_bytes(
                        canonical({"schema_version": 1, "sources": [{**record, "path": path}]})
                    )
                    with self.assertRaisesRegex(ValueError, "source escapes root"):
                        module.audit(snapshot, manifest, sources)
