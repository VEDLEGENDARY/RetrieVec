import io
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import chunk_page, extract_pages, import_manifest
from retrievec.corpus.section_chunks import chunk_page_v2
from retrievec.corpus.snapshot import CorpusError, canonical, digest, load_snapshot


def pdf_bytes(texts: list[str]) -> bytes:
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(612, 792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class ImportTests(unittest.TestCase):
    def test_section_windows_repeat_title_and_bound_overlap(self) -> None:
        analyzer = GoAnalyzer()
        title_only, _ = chunk_page_v2(
            "10 Internet Addiction and Its Cognitive Behavioral Therapy\n\n", analyzer, 32, 4
        )
        self.assertEqual(title_only, ["10 Internet Addiction and Its Cognitive Behavioral Therapy"])
        first, current = chunk_page_v2(
            "1 Methods\nalpha beta gamma delta epsilon zeta eta theta.\n\n"
            "2 Results\niota kappa lambda mu nu xi omicron pi.",
            analyzer,
            8,
            1,
        )
        second, carried = chunk_page_v2("rho sigma tau upsilon", analyzer, 8, 1, current)
        self.assertEqual(carried, "2 Results")
        self.assertTrue(any(chunk.startswith("Section: 1 Methods") for chunk in first))
        self.assertTrue(all(chunk.startswith("Section: 2 Results") for chunk in second))
        self.assertTrue(all(len(tokens) <= 8 for tokens in analyzer.analyze(first + second)))
        self.assertIn("gamma", " ".join(first))
        self.assertIn("upsilon", " ".join(second))
        high_overlap, _ = chunk_page_v2(
            "alpha beta gamma delta epsilon zeta eta theta iota kappa",
            analyzer,
            8,
            7,
        )
        self.assertEqual(len(high_overlap), 3)
        with self.assertRaises(CorpusError):
            chunk_page_v2("1 Heading\ntext", analyzer, 3, 2)

    def test_paragraph_pack_and_oversize_split(self) -> None:
        analyzer = GoAnalyzer()
        for text, budget, expected in (
            ("one two\n\nthree four\n\nfive", 4, ["one two\n\nthree four\n\n", "five"]),
            ("é one two three four!", 2, ["é one ", "two three ", "four!"]),
            ("\r\none\r\n\r\ntwo\r\n", 1, ["\r\none\r\n\r\n", "two\r\n"]),
            ("---\n\none\n\n...", 1, ["---\n\none\n\n..."]),
        ):
            with self.subTest(text=text):
                chunks = chunk_page(text, analyzer.analyze([text])[0], budget)
                self.assertEqual(chunks, expected)
                self.assertEqual("".join(chunks), text)
                self.assertTrue(
                    all(0 < len(tokens) <= budget for tokens in analyzer.analyze(chunks))
                )
        self.assertEqual(chunk_page("...", [], 256), [])
        with self.assertRaises(CorpusError):
            chunk_page("one", [], 0)

    def test_text_and_pdf_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text = "alpha beta\n\nGamma delta!"
            sources = [
                ("a.txt", text.encode()),
                ("b.pdf", pdf_bytes(["Page one evidence", "Page two data"])),
            ]
            records = []
            for name, data in sources:
                (root / name).write_bytes(data)
                records.append(
                    {
                        "paper_id": name,
                        "title": name,
                        "authors": [],
                        "path": name,
                        "source_url": None,
                        "source_sha256": digest(data),
                        "license_note": "synthetic test",
                    }
                )
            manifest = root / "input.json"
            manifest.write_bytes(canonical({"schema_version": 1, "sources": records}))
            output = import_manifest(manifest, root, root / "out", "test", 2)
            first, _, chunks = load_snapshot(output)
            text_chunks = sorted(
                (c for c in chunks if c["paper_id"] == "a.txt"), key=lambda c: c["ordinal"]
            )
            self.assertEqual("".join(c["text"] for c in text_chunks), text)
            self.assertTrue(all(c["page_range"] is None for c in text_chunks))
            pages = {tuple(c["page_range"]) for c in chunks if c["paper_id"] == "b.pdf"}
            self.assertEqual(pages, {(1, 1), (2, 2)})
            manifest.write_bytes(
                canonical({"schema_version": 1, "sources": list(reversed(records))})
            )
            self.assertEqual(output, import_manifest(manifest, root, root / "out", "test", 2))
            changed = import_manifest(manifest, root, root / "out", "test", 3)
            self.assertNotEqual(first["snapshot_id"], load_snapshot(changed)[0]["snapshot_id"])
            changed_ids = {c["chunk_id"] for c in load_snapshot(changed)[2]}
            self.assertTrue({c["chunk_id"] for c in chunks}.isdisjoint(changed_ids))

    def test_failures_leave_no_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("...", encoding="utf-8")
            record = {
                "paper_id": "a",
                "title": "a",
                "authors": [],
                "path": "a.txt",
                "source_url": None,
                "source_sha256": digest(b"..."),
                "license_note": "test",
            }
            manifest = root / "input.json"
            for update in ({}, {"source_sha256": "0" * 64}, {"path": "../escape.txt"}):
                manifest.write_bytes(
                    canonical({"schema_version": 1, "sources": [{**record, **update}]})
                )
                with self.subTest(update=update), self.assertRaises((CorpusError, OSError)):
                    import_manifest(manifest, root, root / "out")
                self.assertFalse((root / "out").exists())

    def test_invalid_extraction_and_pdf_pages(self) -> None:
        for path, data in (("bad.txt", b"\xff"), ("bad.pdf", b"garbage"), ("bad.docx", b"")):
            with self.subTest(path=path), self.assertRaises(CorpusError):
                extract_pages(Path(path), data)
        version, pages = extract_pages(Path("test.pdf"), pdf_bytes(["one", "two"]))
        self.assertIn("pypdf-", version)
        self.assertEqual(pages, [(1, "one"), (2, "two")])
