"""Immutable evidence bundles preserve raw objects, page renders and original PDFs."""

import struct
import zlib
from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest, parse_json
from retrievec.extraction.schema import Evidence
from retrievec.registry.artifacts import identity
from retrievec.registry.worker import publish_bytes


def validate_png(raw):
    if len(raw) > 32 * 1024 * 1024 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("bounded PNG image required")
    offset, width, height, channels, compressed, ended = 8, None, None, None, bytearray(), False
    while offset < len(raw):
        if offset + 12 > len(raw):
            raise ValueError("truncated PNG")
        length = int.from_bytes(raw[offset : offset + 4], "big")
        kind = raw[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(raw):
            raise ValueError("truncated PNG chunk")
        data = raw[offset + 8 : offset + 8 + length]
        crc = int.from_bytes(raw[offset + 8 + length : end], "big")
        if zlib.crc32(kind + data) & 0xFFFFFFFF != crc:
            raise ValueError("PNG checksum mismatch")
        if kind == b"IHDR":
            if width is not None or offset != 8 or length != 13:
                raise ValueError("invalid PNG header")
            width, height, bits, color, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", data
            )
            if not 1 <= width * height <= 16_000_000 or bits != 8 or color not in (2, 6):
                raise ValueError("bounded 8-bit RGB/RGBA PNG required")
            if compression or filtering or interlace:
                raise ValueError("unsupported PNG encoding")
            channels = 3 if color == 2 else 4
        elif kind == b"IDAT":
            if width is None:
                raise ValueError("PNG data precedes header")
            compressed.extend(data)
        elif kind == b"IEND":
            if length or end != len(raw):
                raise ValueError("invalid PNG ending")
            ended = True
        elif kind not in (b"pHYs", b"sRGB", b"gAMA", b"cHRM"):
            raise ValueError("unsupported PNG chunk")
        offset = end
    if not ended or not width or not height:
        raise ValueError("incomplete PNG")
    expected = height * (1 + width * channels)
    decoder = zlib.decompressobj()
    decoded = decoder.decompress(bytes(compressed), expected + 1)
    if (
        len(decoded) != expected
        or not decoder.eof
        or decoder.unused_data
        or decoder.unconsumed_tail
    ):
        raise ValueError("invalid or oversized PNG pixel stream")
    return width, height


class EvidenceStore:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def image(self, checksum):
        return self.root / "evidence-images" / (identity(checksum, "") + ".png")

    def read(self, evidence_id):
        path = self.root / "evidence" / (identity(evidence_id, "eo_") + ".json")
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(self.root)
            or path.stat().st_size > 4 * 1024 * 1024
        ):
            raise ValueError("invalid evidence artifact")
        evidence = Evidence.model_validate(parse_json(path.read_bytes()))
        if evidence.identity != evidence_id:
            raise ValueError("evidence identity mismatch")
        return evidence

    def bundle(self, bundle_id):
        path = self.root / "evidence-bundles" / (identity(bundle_id, "eb_") + ".json")
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(self.root)
            or path.stat().st_size > 4 * 1024 * 1024
        ):
            raise ValueError("invalid evidence bundle")
        value = parse_json(path.read_bytes())
        if "eb_" + digest(canonical(value)) != bundle_id:
            raise ValueError("evidence bundle identity mismatch")
        if value.get("schema_version") != 1 or not isinstance(value.get("evidence_ids"), list):
            raise ValueError("invalid evidence bundle schema")
        objects = [self.read(key) for key in value["evidence_ids"]]
        if any(item.source_sha256 != value["source_sha256"] for item in objects):
            raise ValueError("evidence bundle mixes sources")
        if not 1 <= len(objects) <= 10000 or len({item.identity for item in objects}) != len(
            objects
        ):
            raise ValueError("invalid evidence bundle object count")
        return value, objects

    def publish(self, source, evidence, images):
        from retrievec.extraction.pages import inspect_pdf

        if not 1 <= len(evidence) <= 10000:
            raise ValueError("invalid evidence count")
        pages = {row["geometry"].page: row["geometry"] for row in inspect_pdf(source)}
        source_hash = digest(source)
        objects = [Evidence.model_validate(item.model_dump(mode="json")) for item in evidence]
        if len({item.identity for item in objects}) != len(objects):
            raise ValueError("duplicate evidence")
        layers_by_page = {}
        for item in objects:
            if item.content.kind == "prose":
                layers_by_page.setdefault(item.geometry.page, set()).add(item.derivation)
        for item in objects:
            if item.source_sha256 != source_hash or pages.get(item.geometry.page) != item.geometry:
                raise ValueError("evidence locator does not match original PDF")
            layers = layers_by_page.get(item.geometry.page, set())
            if "ocr" in layers and "text_layer" in layers:
                raise ValueError("one page cannot index both OCR and its text layer")
            for checksum in (item.page_render_sha256, item.region_crop_sha256):
                if checksum is not None:
                    raw = images[checksum]
                    if digest(raw) != checksum:
                        raise ValueError("image identity mismatch")
                    width, height = validate_png(raw)
                    if checksum == item.page_render_sha256:
                        expected_width, expected_height = item.geometry.display_size
                        if abs(width / height - expected_width / expected_height) > 2 / height:
                            raise ValueError(
                                "page render does not match displayed page aspect ratio"
                            )
                    if not self.image(checksum).resolve().is_relative_to(self.root):
                        raise ValueError("image path escapes retained store")
                    publish_bytes(self.image(checksum), raw)
            target = self.root / "evidence" / (item.identity + ".json")
            if not target.resolve().is_relative_to(self.root):
                raise ValueError("evidence path escapes retained store")
            publish_bytes(target, canonical(item.model_dump(mode="json")) + b"\n")
        original = self.root / "evidence-sources" / (source_hash + ".pdf")
        if not original.resolve().is_relative_to(self.root):
            raise ValueError("original path escapes retained store")
        publish_bytes(original, source)
        value = {
            "schema_version": 1,
            "source_sha256": source_hash,
            "evidence_ids": sorted(item.identity for item in objects),
        }
        key = "eb_" + digest(canonical(value))
        target = self.root / "evidence-bundles" / (key + ".json")
        if not target.resolve().is_relative_to(self.root):
            raise ValueError("bundle path escapes retained store")
        publish_bytes(target, canonical(value) + b"\n")
        return key
