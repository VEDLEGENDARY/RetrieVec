import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from retrievec.corpus.snapshot import (
    CorpusError,
    canonical,
    encode_snapshot,
    load_snapshot,
    make_chunk,
    make_paper,
    parse_json,
    publish_snapshot,
    validate_records,
)

ROOT = Path(__file__).resolve().parents[2]


class SnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.paper = make_paper(
            paper_id="p",
            title="Evidence",
            authors=["A. Author"],
            source=b"source",
            source_url=None,
            extraction_version="text-v1",
            license_note="synthetic",
        )
        self.chunk = make_chunk(self.paper, "dense retrieval", 0, "c", "whole-v1", [1, 2])

    def test_canonical_known_bytes(self) -> None:
        self.assertEqual(canonical({"z": "é<😀", "a": 1}), b'{"a":1,"z":"\\u00e9<\\ud83d\\ude00"}')

    def test_determinism_and_configuration_identity(self) -> None:
        second = make_chunk(self.paper, "other evidence", 1, "c", "whole-v1")
        first = encode_snapshot([self.paper], [self.chunk, second], "c", {"budget": 256})
        repeat = encode_snapshot([self.paper], [second, self.chunk], "c", {"budget": 256})
        self.assertEqual(first, repeat)
        different = encode_snapshot([self.paper], [second, self.chunk], "c", {"budget": 128})
        self.assertNotEqual(first[0]["snapshot_id"], different[0]["snapshot_id"])
        changed = make_chunk(self.paper, "changed", 0, "c", "whole-v1")
        self.assertNotEqual(self.chunk["chunk_id"], changed["chunk_id"])
        self.assertNotEqual(
            first[0]["snapshot_id"],
            encode_snapshot([self.paper], [changed], "c", {})[0]["snapshot_id"],
        )

    def test_invalid_records(self) -> None:
        changes = [
            ("schema_version", 2),
            ("schema_version", True),
            ("text", " "),
            ("text", "wrong hash"),
            ("text", "\ud800"),
            ("paper_version_id", "missing"),
            ("paper_id", "missing"),
            ("ordinal", -1),
            ("ordinal", True),
            ("ordinal", 2),
            ("collection_id", "other"),
            ("page_range", [2, 1]),
            ("page_range", [True, 2]),
            ("chunk_id", "wrong"),
            ("text_sha256", "x"),
        ]
        for field, value in changes:
            with self.subTest(field=field, value=repr(value)):
                bad = {**self.chunk, field: value}
                with self.assertRaises(CorpusError):
                    validate_records([self.paper], [bad], "c")
        for papers, chunks in (
            ([self.paper] * 2, [self.chunk]),
            ([self.paper], [self.chunk] * 2),
            ([self.paper], []),
        ):
            with self.assertRaises(CorpusError):
                validate_records(papers, chunks, "c")
        for field, value in (
            ("source_sha256", "0" * 64),
            ("authors", "name"),
            ("license_note", ""),
            ("source_url", "file:///secret"),
        ):
            with self.subTest(field=field), self.assertRaises(CorpusError):
                validate_records([{**self.paper, field: value}], [self.chunk], "c")

    def test_round_trip_and_idempotent_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = publish_snapshot(root, [self.paper], [self.chunk], "c", {})
            self.assertEqual(load_snapshot(target)[1:], ([self.paper], [self.chunk]))
            self.assertEqual(publish_snapshot(root, [self.paper], [self.chunk], "c", {}), target)
            self.assertEqual(len(list(root.iterdir())), 1)

    def test_validation_failure_does_not_publish(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("retrievec.corpus.snapshot.load_snapshot", side_effect=CorpusError("bad")):
                with self.assertRaises(CorpusError):
                    publish_snapshot(root, [self.paper], [self.chunk], "c", {})
            self.assertEqual(list(root.iterdir()), [])

    def test_corruption_rejected(self) -> None:
        _, files = encode_snapshot([self.paper], [self.chunk], "c", {})
        for name, data in (
            ("papers.jsonl", b"\xff\n"),
            ("chunks.jsonl", b"{}\n"),
            ("chunks.jsonl", files["chunks.jsonl"] + b"\n"),
            ("manifest.json", b'{"schema_version":999}\n'),
        ):
            with (
                self.subTest(name=name, data=data[:20]),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                for filename, original in files.items():
                    (root / filename).write_bytes(data if filename == name else original)
                with self.assertRaises(CorpusError):
                    load_snapshot(root)

    def test_manifest_provenance_and_counts_verified(self) -> None:
        manifest, files = encode_snapshot([self.paper], [self.chunk], "c", {})
        for field in ("counts", "files", "sources", "snapshot_id", "extraction_versions"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for name, data in files.items():
                    (root / name).write_bytes(data)
                changed = copy.deepcopy(manifest)
                changed[field] = None
                (root / "manifest.json").write_bytes(canonical(changed) + b"\n")
                with self.assertRaises(CorpusError):
                    load_snapshot(root)

    def test_strict_json(self) -> None:
        for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b'"\xff"', b"{} garbage"):
            with self.subTest(data=data), self.assertRaises(CorpusError):
                parse_json(data)

    def test_committed_synthetic_snapshot(self) -> None:
        snapshots = list((ROOT / "datasets/fixtures/snapshots").iterdir())
        self.assertEqual(len(snapshots), 1)
        manifest, papers, chunks = load_snapshot(snapshots[0])
        self.assertEqual(manifest["counts"], {"papers": 12, "chunks": 12})
        sources = json.loads((ROOT / "datasets/fixtures/synthetic_sources.json").read_text("utf-8"))
        by_paper = {chunk["paper_id"]: chunk for chunk in chunks}
        self.assertEqual({paper["paper_id"] for paper in papers}, set(by_paper))
        for source in sources:
            self.assertEqual(by_paper[source["paper_id"]]["text"], source["text"])
