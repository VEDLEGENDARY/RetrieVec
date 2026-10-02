import unittest
from types import SimpleNamespace

from retrievec.extraction.docling_adapter import source_box
from retrievec.extraction.schema import PageGeometry


class DoclingCoordinatesTests(unittest.TestCase):
    def test_page_relative_boxes_respect_crop_offset_and_origin(self):
        geometry = PageGeometry(
            page=1,
            media_box=(0, 0, 612, 792),
            crop_box=(10, 20, 610, 780),
        )
        bottom = SimpleNamespace(
            bbox=SimpleNamespace(l=20, b=30, r=120, t=90, coord_origin="BOTTOMLEFT")
        )
        top = SimpleNamespace(
            bbox=SimpleNamespace(l=20, t=670, r=120, b=730, coord_origin="TOPLEFT")
        )
        self.assertEqual(source_box(bottom, geometry), (30, 50, 130, 110))
        self.assertEqual(source_box(top, geometry), (30, 50, 130, 110))
        outside = SimpleNamespace(
            bbox=SimpleNamespace(l=20, b=30, r=700, t=90, coord_origin="BOTTOMLEFT")
        )
        with self.assertRaises(ValueError):
            source_box(outside, geometry)

    def test_rotated_pages_fail_before_publication(self):
        geometry = PageGeometry(
            page=1,
            media_box=(0, 0, 612, 792),
            crop_box=(0, 0, 612, 792),
            rotation=90,
        )
        provenance = SimpleNamespace(
            bbox=SimpleNamespace(l=20, b=30, r=120, t=90, coord_origin="BOTTOMLEFT")
        )
        with self.assertRaises(ValueError):
            source_box(provenance, geometry)
