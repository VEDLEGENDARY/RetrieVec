"""Exact page-text/glyph alignment; unsupported layouts never acquire guessed boxes."""

import io
import math

import pdfplumber

from retrievec.corpus.snapshot import canonical, digest, parse_json
from retrievec.registry.artifacts import identity
from retrievec.registry.worker import publish_bytes


class PDFLocations:
    def __init__(self, source, root):
        self.document = pdfplumber.open(io.BytesIO(source))
        self.root = root
        self.source_hash = digest(source)

    def close(self):
        self.document.close()

    def page(self, number, text):
        page = self.document.pages[number - 1]
        if (
            page.rotation
            or tuple(page.cropbox) != tuple(page.mediabox)
            or page.page_obj.attrs.get("UserUnit", 1) != 1
        ):
            return None, "Rotated or cropped page: verified display coordinates unavailable."
        chars = [c for c in page.chars if not c["text"].isspace()]
        indices = [index for index, char in enumerate(text) if not char.isspace()]
        if "".join(c["text"] for c in chars) != "".join(text[i] for i in indices):
            return None, "Extracted text and PDF glyph order differ; coordinates were not inferred."
        if any(len(c["text"]) != 1 for c in chars):
            return None, "Multi-character PDF glyphs cannot be aligned exactly."
        boxes = [[c["x0"], c["top"], c["x1"], c["bottom"]] for c in chars]
        if any(
            not all(math.isfinite(v) for v in box)
            or not (0 <= box[0] < box[2] <= page.width and 0 <= box[1] < box[3] <= page.height)
            for box in boxes
        ):
            return None, "PDF glyph coordinates are outside the verified page surface."
        image = page.to_image(resolution=96, antialias=True, force_mediabox=True)
        output = io.BytesIO()
        image.original.save(output, format="PNG")
        raw = output.getvalue()
        if len(raw) > 32 * 1024 * 1024:
            return None, "Rendered page exceeds the retained image size limit."
        checksum = digest(raw)
        publish_bytes(self.root / "pdf-pages" / (checksum + ".png"), raw)
        return {
            "indices": indices,
            "boxes": boxes,
            "width": page.width,
            "height": page.height,
            "image_sha256": checksum,
        }, None

    def passage(self, page, limitation, number, begin, end, chunk):
        locator = None
        if page is not None:
            selected = [
                box
                for index, box in zip(page["indices"], page["boxes"], strict=True)
                if begin <= index < end
            ]
            if selected:
                locator = {
                    "page": number,
                    "width": page["width"],
                    "height": page["height"],
                    "boxes": selected,
                    "image_sha256": page["image_sha256"],
                    "coordinates": "PDF points; top-left page origin",
                    "extractor": "pdfplumber-0.11.10-exact-glyph-alignment-v1",
                }
        return {
            "source_sha256": self.source_hash,
            "text_sha256": chunk["text_sha256"],
            "pdf_locator": locator,
            "locator_limitation": limitation if locator is None else None,
            "text_offsets": {
                "unit": "Unicode code points in extracted page text",
                "page": number,
                "start": begin,
                "end": end,
            },
        }


def publish_locations(root, mapping):
    value = {"schema_version": 1, "chunks": mapping}
    key = "pl_" + digest(canonical(value))
    publish_bytes(root / "pdf-locations" / (key + ".json"), canonical(value) + b"\n")
    return key


class LocationIndex:
    def __init__(self, root, corpus):
        self.mapping = {}
        key = corpus["configuration"].get("pdf_locations_id")
        if key is None:
            return
        path = root / "pdf-locations" / (identity(key, "pl_") + ".json")
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())
            or path.stat().st_size > 64 * 1024 * 1024
        ):
            raise ValueError("invalid PDF locator path")
        value = parse_json(path.read_bytes())
        if "pl_" + digest(canonical(value)) != key or value["schema_version"] != 1:
            raise ValueError("PDF locator identity mismatch")
        self.mapping = value["chunks"]

    def attributes(self, chunk, paper):
        row = self.mapping.get(chunk["chunk_id"])
        if row is None:
            return {
                "pdf_locator": None,
                "locator_limitation": "No verified PDF location retained for this passage.",
            }
        if (
            row["source_sha256"] != paper["source_sha256"]
            or row["text_sha256"] != chunk["text_sha256"]
        ):
            raise ValueError("PDF locator belongs to different source text")
        return {key: row[key] for key in ("pdf_locator", "locator_limitation", "text_offsets")}
