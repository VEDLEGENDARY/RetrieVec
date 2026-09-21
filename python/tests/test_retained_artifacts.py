import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from retrievec.corpus.snapshot import canonical, digest
from retrievec.registry.backup import inventory
from retrievec.registry.retention import audit_retained


class RetainedArtifactTests(unittest.TestCase):
    def database(self, *, sources=(), inputs=()):
        db = MagicMock()
        missing = MagicMock()
        missing.fetchone.return_value = None
        db.execute.side_effect = [missing, iter(()), iter(sources), iter(inputs)]
        return db

    def test_pending_ingestion_keeps_its_original_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "inputs").mkdir()
            (root / "sources").mkdir()
            name = "a" * 32 + ".txt"
            source = root / "sources" / name
            source.write_bytes(b"original synthetic paper")
            raw = canonical(
                {
                    "schema_version": 1,
                    "sources": [{"path": name, "source_sha256": digest(source.read_bytes())}],
                }
            )
            key = digest(raw)
            (root / "inputs" / (key + ".json")).write_bytes(raw)
            inputs = [{"payload": {"input": {"manifest_hash": key}}}]
            result = audit_retained(self.database(inputs=inputs), root, inventory(root))
            self.assertEqual(result["pending_inputs"], 1)
            source.unlink()
            with self.assertRaisesRegex(ValueError, "referenced artifact"):
                audit_retained(self.database(inputs=inputs), root, inventory(root))

    def test_original_source_owner_must_match_collection_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            row = {
                "owner_id": "reader",
                "collection_owner": "owner",
                "storage_key": "a" * 32 + ".txt",
                "source_hash": "b" * 64,
                "size_bytes": 10,
            }
            with self.assertRaisesRegex(ValueError, "ownership"):
                audit_retained(self.database(sources=[row]), Path(temporary), [])

    def test_ready_snapshot_cannot_be_missing_its_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            db = MagicMock()
            missing = MagicMock()
            missing.fetchone.return_value = None
            db.execute.side_effect = [missing, iter([{"snapshot_id": "rs_" + "a" * 64}])]
            with self.assertRaises(OSError):
                audit_retained(db, Path(temporary), [])
