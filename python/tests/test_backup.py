import json
import tempfile
import unittest
from pathlib import Path

from retrievec.registry.backup import checksum, disjoint, inventory, verify


class BackupBundleTests(unittest.TestCase):
    def test_corruption_and_interrupted_bundles_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = root / "store"
            store.mkdir()
            (store / "evidence.txt").write_bytes(b"synthetic evidence")
            (root / "metadata.dump").write_bytes(b"synthetic dump")
            manifest = {
                "schema_version": 1,
                "session_rows": "excluded",
                "files": inventory(store),
                "dump_sha256": checksum(root / "metadata.dump"),
            }
            (root / "manifest.json").write_text(json.dumps(manifest))
            self.assertEqual(verify(root), manifest)
            (root / "INCOMPLETE").touch()
            with self.assertRaises(ValueError):
                verify(root)
            (root / "INCOMPLETE").unlink()
            (store / "evidence.txt").write_bytes(b"changed evidence")
            with self.assertRaises(ValueError):
                verify(root)

    def test_nested_destinations_cannot_replace_source_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for left, right in [(root, root), (root, root / "child"), (root / "child", root)]:
                with self.assertRaises(ValueError):
                    disjoint(left, right)
