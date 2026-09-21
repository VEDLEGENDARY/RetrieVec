import io
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

import pypdf
from retrievec.corpus.snapshot import digest
from retrievec.extraction.evaluation import prose_metrics, table_metrics
from retrievec.extraction.pages import classify, reading_order
from retrievec.extraction.representation import numeric_text, searchable
from retrievec.extraction.schema import Cell, Equation, Evidence, PageGeometry, Prose, Review, Table
from retrievec.extraction.store import EvidenceStore, validate_png


def png():
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00" + b"\xff" * 6 + b"\x00" + b"\xff" * 6))
        + chunk(b"IEND", b"")
    )


def evidence(**changes):
    fields = dict(
        source_sha256="a" * 64,
        geometry=PageGeometry(
            page=1, media_box=(0.0, 0.0, 100.0, 100.0), crop_box=(0.0, 0.0, 100.0, 100.0)
        ),
        bbox=(10.0, 10.0, 90.0, 90.0),
        page_render_sha256=digest(png()),
        extractor="fixture",
        revision="synthetic-v1",
        raw_output="synthetic output",
        content=Prose(text="Synthetic prose"),
        derivation="text_layer",
    )
    fields.update(changes)
    return Evidence(**fields)


class AdvancedExtractionTests(unittest.TestCase):
    def test_crop_rotation_and_user_units_have_explicit_transforms(self):
        expected = {
            0: (0, 160, 20, 200),
            90: (0, 0, 40, 20),
            180: (80, 0, 100, 40),
            270: (160, 80, 200, 100),
        }
        for rotation, box in expected.items():
            page = PageGeometry(
                page=1,
                media_box=(0, 0, 200, 300),
                crop_box=(10, 20, 110, 220),
                rotation=rotation,
                user_unit=2,
            )
            self.assertEqual(page.display_box((10, 20, 30, 60)), tuple(v * 2 for v in box))
            with self.assertRaises(ValueError):
                page.display_box((0, 0, 30, 60))

    def test_tables_preserve_headers_spans_units_and_ambiguity(self):
        table = Table(
            rows=2,
            columns=2,
            cells=[
                Cell(row=0, column=0, column_span=2, role="column_header", text="Accuracy"),
                Cell(row=1, column=0, text="87.2", unit="percent"),
                Cell(row=1, column=1, text="", missing=True, ambiguous=True),
            ],
        )
        item = evidence(content=table)
        self.assertIn("Accuracy", searchable(item))
        self.assertIn("87.2; unit=percent", searchable(item))
        self.assertIn("missing", searchable(item))
        self.assertNotIn("Row 2", numeric_text(item))
        self.assertFalse(item.synthesis_allowed)
        with self.assertRaises(ValueError):
            Table(
                rows=1,
                columns=2,
                cells=[
                    Cell(row=0, column=0, column_span=2, text="merged"),
                    Cell(row=0, column=1, text="overlap"),
                ],
            )

    def test_uncertain_transcriptions_cannot_support_generation(self):
        self.assertFalse(evidence(derivation="ocr").synthesis_allowed)
        self.assertFalse(
            evidence(
                content=Equation(transcription="x=1"), region_crop_sha256=digest(png())
            ).synthesis_allowed
        )
        original = evidence()
        reviewed = evidence(
            review=Review(
                status="reviewed",
                reviewer="synthetic-test",
                rationale="Test-only schema transition",
            )
        )
        self.assertNotEqual(original.identity, reviewed.identity)
        with self.assertRaises(ValueError):
            Review(status="reviewed")

    def test_classification_is_per_page_and_reading_order_uses_regions(self):
        self.assertEqual(classify("", True)["action"], "ocr_required")
        self.assertEqual(classify("Readable source text " * 8, True)["action"], "retain_text_layer")
        left_top = evidence(bbox=(0, 80, 30, 95), content=Prose(text="left top"))
        left_bottom = evidence(bbox=(0, 10, 30, 70), content=Prose(text="left bottom"))
        right = evidence(bbox=(60, 10, 90, 95), content=Prose(text="right column"))
        ordered = reading_order([right, left_bottom, left_top])
        self.assertEqual(
            [item.content.text for item in ordered], ["left top", "left bottom", "right column"]
        )

    def test_bundle_retains_source_and_rejects_double_text_layers(self):
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=100, height=100)
        stream = io.BytesIO()
        writer.write(stream)
        source, image = stream.getvalue(), png()
        item = evidence(source_sha256=digest(source))
        with tempfile.TemporaryDirectory() as temporary:
            store = EvidenceStore(Path(temporary))
            bundle = store.publish(source, [item], {digest(image): image})
            _, retained = store.bundle(bundle)
            self.assertEqual(retained[0].identity, item.identity)
            self.assertEqual(validate_png(image), (2, 2))
            with self.assertRaises(ValueError):
                store.publish(
                    source,
                    [item, evidence(source_sha256=digest(source), derivation="ocr")],
                    {digest(image): image},
                )
            with self.assertRaises(ValueError):
                validate_png(image[:-1])

    def test_metrics_do_not_claim_semantic_or_equation_review(self):
        metrics = prose_metrics("a cat", "a bat")
        self.assertEqual(metrics["character_edits"], 1)
        self.assertEqual(metrics["word_error_rate"], 0.5)
        table = Table(rows=1, columns=1, cells=[Cell(row=0, column=0, text="10", unit="ms")])
        wrong = Table(rows=1, columns=1, cells=[Cell(row=0, column=0, text="10", unit="s")])
        self.assertEqual(table_metrics(table, wrong)["exact_numeric_and_unit_matches"], 0)
