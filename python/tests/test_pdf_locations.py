import tempfile
import unittest
from pathlib import Path

from retrievec.corpus.importer import extract_pages, import_manifest
from retrievec.corpus.pdf_locations import LocationIndex, PDFLocations
from retrievec.corpus.snapshot import canonical, digest, load_snapshot
from test_importer import pdf_bytes


class PDFLocationTests(unittest.TestCase):
    def test_exact_offsets_boxes_and_hash_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = pdf_bytes(["Evidence repeats Evidence"])
            (root / "paper.pdf").write_bytes(source)
            row = {
                "paper_id": "paper",
                "title": "Title",
                "authors": [],
                "path": "paper.pdf",
                "source_sha256": digest(source),
                "source_url": None,
                "license_note": "Fixture",
            }
            manifest = root / "input.json"
            manifest.write_bytes(canonical({"schema_version": 1, "sources": [row]}))
            path = import_manifest(manifest, root, root / "corpora", token_budget=1)
            corpus, papers, chunks = load_snapshot(path)
            index = LocationIndex(root, corpus)
            first = index.attributes(chunks[0], papers[0])
            last = index.attributes(chunks[-1], papers[0])
            self.assertEqual(first["text_offsets"]["start"], 0)
            self.assertEqual(first["pdf_locator"]["page"], 1)
            self.assertAlmostEqual(first["pdf_locator"]["boxes"][0][0], 72)
            self.assertGreater(
                last["pdf_locator"]["boxes"][0][0], first["pdf_locator"]["boxes"][-1][2]
            )
            image = root / "pdf-pages" / (first["pdf_locator"]["image_sha256"] + ".png")
            self.assertEqual(digest(image.read_bytes()), first["pdf_locator"]["image_sha256"])
            altered = {**chunks[0], "text_sha256": "0" * 64}
            with self.assertRaisesRegex(ValueError, "different source text"):
                index.attributes(altered, papers[0])
            experimental = import_manifest(
                manifest,
                root,
                root / "corpora",
                token_budget=8,
                chunker="paragraph-v2",
                overlap=1,
            )
            v2_corpus, v2_papers, v2_chunks = load_snapshot(experimental)
            location = LocationIndex(root, v2_corpus).attributes(v2_chunks[0], v2_papers[0])
            self.assertIsNone(location["pdf_locator"])
            self.assertIn("No verified PDF location", location["locator_limitation"])

    def test_alignment_failure_never_guesses_coordinates(self):
        with tempfile.TemporaryDirectory() as directory:
            source = pdf_bytes(["Evidence"])
            extractor = PDFLocations(source, Path(directory))
            try:
                page, limitation = extractor.page(1, "Changed extraction")
                self.assertIsNone(page)
                self.assertIn("not inferred", limitation)
                _, pages = extract_pages(Path("test.pdf"), source)
                matched, _ = extractor.page(1, pages[0][1])
                self.assertIsNotNone(matched)
            finally:
                extractor.close()
