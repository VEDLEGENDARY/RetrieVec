import gzip
import json
import tempfile
import unittest
from pathlib import Path

from retrievec.evaluation.report_io import load_report, pack_report


class ReportArchiveTests(unittest.TestCase):
    def test_plain_and_archive_preserve_every_original_byte_and_review_field(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "measured.json"
            data = {
                "score": 0.588,
                "interval": [-0.01, 0.02],
                "human_review": None,
                "text": "évidence",
                "failures": [{"query": "one"}],
            }
            raw = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            path.write_bytes(raw)
            self.assertEqual(load_report(path), data)
            metadata = pack_report(path, remove_original=True)
            archive = path.with_suffix(".json.gz")
            self.assertFalse(path.exists())
            self.assertEqual(gzip.decompress(archive.read_bytes()), raw)
            self.assertEqual(archive.read_bytes()[4:8], bytes(4))
            self.assertEqual(load_report(archive), data)
            self.assertEqual(metadata["uncompressed_bytes"], len(raw))

    def test_existing_archive_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "measured.json"
            path.write_text('{"version": 1}', encoding="utf-8")
            pack_report(path)
            archive = path.with_suffix(".json.gz")
            original = archive.read_bytes()
            path.write_text('{"version": 2}', encoding="utf-8")
            with self.assertRaises(FileExistsError):
                pack_report(path, remove_original=True)
            self.assertEqual(archive.read_bytes(), original)
            self.assertEqual(load_report(path), {"version": 2})

    def test_malformed_json_and_corrupt_archives_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_bytes(b"not JSON")
            with self.assertRaises(json.JSONDecodeError):
                pack_report(path, remove_original=True)
            self.assertTrue(path.exists())
            archive = path.with_suffix(".json.gz")
            self.assertFalse(archive.exists())
            archive.write_bytes(b"not gzip")
            with self.assertRaises(gzip.BadGzipFile):
                load_report(archive)
