"""Bounded, per-page extraction routing; classifications are heuristics, not quality labels."""

import io
import unicodedata

import pypdf

from retrievec.extraction.schema import PageGeometry

CLASSIFIER_VERSION = "page-routing-v1"


def classify(text, has_images):
    visible = [character for character in text if not character.isspace()]
    bad = sum(
        character == "\ufffd" or unicodedata.category(character) in ("Cc", "Cs")
        for character in visible
    )
    alphanumeric = sum(character.isalnum() for character in visible)
    count = len(visible)
    sufficient = count >= 40 and alphanumeric / max(1, count) >= 0.5 and bad / max(1, count) <= 0.02
    if sufficient:
        mode = "text_with_images" if has_images else "text_layer"
        action = "retain_text_layer"
    elif has_images:
        mode, action = "insufficient_text_with_images", "ocr_required"
    elif count:
        mode, action = "sparse_or_uncertain_text", "inspection_required"
    else:
        mode, action = "empty_or_vector_page", "inspection_required"
    return {
        "version": CLASSIFIER_VERSION,
        "mode": mode,
        "action": action,
        "visible_characters": count,
        "replacement_or_control_count": bad,
        "alphanumeric_fraction": alphanumeric / max(1, count),
        "warnings": ["image_content_not_interpreted"] if has_images else [],
    }


def inspect_pdf(source, max_pages=100):
    if not 1 <= max_pages <= 500 or len(source) > 64 * 1024 * 1024:
        raise ValueError("PDF resource limit exceeded")
    reader = pypdf.PdfReader(io.BytesIO(source), strict=True)
    if reader.is_encrypted:
        raise ValueError("encrypted PDF is unsupported")
    if len(reader.pages) > max_pages:
        raise ValueError("PDF page limit exceeded")
    pages, total = [], 0
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text(extraction_mode="plain") or ""
        total += len(text.encode("utf-8"))
        if total > 10 * 1024 * 1024:
            raise ValueError("extracted text limit exceeded")
        # Inspect resource declarations without decoding image streams. Forms may contain
        # nested images, so an XObject form also triggers conservative visual inspection.
        resources = page.get("/Resources", {})
        if hasattr(resources, "get_object"):
            resources = resources.get_object()
        objects = resources.get("/XObject", {})
        if hasattr(objects, "get_object"):
            objects = objects.get_object()
        visual = any(
            value.get_object().get("/Subtype") in ("/Image", "/Form") for value in objects.values()
        )
        geometry = PageGeometry(
            page=number,
            media_box=tuple(float(v) for v in page.mediabox),
            crop_box=tuple(float(v) for v in page.cropbox),
            rotation=int(page.rotation) % 360,
            user_unit=float(page.get("/UserUnit", 1)),
        )
        pages.append({"geometry": geometry, "text": text, "classification": classify(text, visual)})
    return pages


def reading_order(evidence):
    """Deterministic XY-cut over supplied real regions; never infer character boxes."""
    if not evidence:
        return []
    if len(evidence) > 10000:
        raise ValueError("too many reading-order regions")
    geometry = evidence[0].geometry
    if any(
        item.geometry != geometry or item.source_sha256 != evidence[0].source_sha256
        for item in evidence
    ):
        raise ValueError("reading order requires one source page")
    boxes = {item.identity: geometry.display_box(item.bbox) for item in evidence}
    if len(boxes) != len(evidence):
        raise ValueError("duplicate evidence region")

    def order(items, depth=0):
        if len(items) <= 1:
            return items
        # Find whitespace separating whole regions, preferring columns. Full-width
        # headings force a horizontal split first; recursion then orders each band.
        if depth < 32:
            for axis in (0, 1):
                sorted_items = sorted(items, key=lambda item: boxes[item.identity][axis])
                end = boxes[sorted_items[0].identity][axis + 2]
                for index, item in enumerate(sorted_items[1:], 1):
                    box = boxes[item.identity]
                    if box[axis] - end >= (12 if axis == 0 else 3):
                        return order(sorted_items[:index], depth + 1) + order(
                            sorted_items[index:], depth + 1
                        )
                    end = max(end, box[axis + 2])
        return sorted(
            items,
            key=lambda item: (boxes[item.identity][1], boxes[item.identity][0], item.identity),
        )

    return order(evidence)


def select_prose(text_layer, ocr, route):
    """Choose exactly one prose layer per page, including mixed documents."""
    chosen = text_layer if route["action"] == "retain_text_layer" else ocr
    if any(item.content.kind != "prose" for item in chosen):
        raise ValueError("prose selection received structured objects")
    return reading_order(chosen)
