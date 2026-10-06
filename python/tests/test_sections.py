import tempfile
import unittest
from pathlib import Path

from retrievec.corpus.importer import import_manifest
from retrievec.corpus.sections import PassageProvenance, segments
from retrievec.corpus.snapshot import canonical, digest, load_snapshot


class SectionTests(unittest.TestCase):
    def test_only_explicit_headings_are_boundaries_and_pages_carry_context(self):
        text = "Preface\n\n## Abstract\nA finding.\n\n2 Methods\nA method.\nResults improve.\n"
        spans, current, heading = segments(text)
        self.assertEqual([span[2] for span in spans], ["unclassified", "abstract", "methods"])
        self.assertEqual("".join(text[a:b] for a, b, _, _ in spans), text)
        following, _, _ = segments("Continued method.\n", current, heading)
        self.assertEqual(following[0][2], "methods")

    def test_opt_in_preserves_exact_text_and_immutable_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text = "Abstract\nA finding.\n\nMethods\nOne method.\n\nResults\nOne result.\n"
            (root / "paper.txt").write_bytes(text.encode())
            manifest = root / "manifest.json"
            manifest.write_bytes(
                canonical(
                    {
                        "schema_version": 1,
                        "sources": [
                            {
                                "paper_id": "paper",
                                "title": "Title",
                                "authors": [],
                                "source_url": None,
                                "source_sha256": digest(text.encode()),
                                "path": "paper.txt",
                                "license_note": "Fixture",
                            }
                        ],
                    }
                )
            )
            plain = import_manifest(manifest, root, root / "corpora", "collection", 96)
            aware = import_manifest(
                manifest, root, root / "corpora", "collection", 96, section_aware=True
            )
            self.assertNotEqual(plain, aware)
            corpus, _, chunks = load_snapshot(aware)
            chunks.sort(key=lambda row: row["ordinal"])
            self.assertEqual("".join(row["text"] for row in chunks), text)
            index = PassageProvenance(root, corpus)
            self.assertEqual(
                [index.attributes(c)["section"] for c in chunks], ["abstract", "methods", "results"]
            )
            for chunk in chunks:
                offsets = index.attributes(chunk)["text_offsets"]
                self.assertEqual(text[offsets["start"] : offsets["end"]], chunk["text"])
            key = corpus["configuration"]["passage_provenance_id"]
            (root / "passage-provenance" / (key + ".json")).write_bytes(b"{}")
            with self.assertRaises((ValueError, KeyError)):
                PassageProvenance(root, corpus)
