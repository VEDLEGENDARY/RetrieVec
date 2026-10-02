"""Optional offline Docling layout adapter for the existing evidence protocol.

Install the ``layout`` extra in a separate environment, prefetch Docling model
weights, then pin the installed entry point's SHA256 in AdapterConfig. The
normal upload/import path never loads Docling or changes its default behavior.
"""

import argparse
import io
import os
from importlib.metadata import version
from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest, parse_json
from retrievec.extraction.schema import Evidence, PageGeometry

DOCLING_VERSION = "2.129.0"
EXTRACTOR = "docling-layout"
REVISION = f"{DOCLING_VERSION}+adapter-v1"


def source_box(provenance, geometry: PageGeometry):
    """Map Docling page-relative coordinates into unrotated PDF user space."""
    if geometry.rotation or geometry.user_unit != 1:
        raise ValueError("Docling adapter requires an unrotated unit-scale PDF page")
    box = provenance.bbox
    crop = geometry.crop_box
    height = crop[3] - crop[1]
    origin = str(box.coord_origin).lower()
    if "bottomleft" in origin or "bottom_left" in origin:
        bounds = (crop[0] + box.l, crop[1] + box.b, crop[0] + box.r, crop[1] + box.t)
    elif "topleft" in origin or "top_left" in origin:
        bounds = (
            crop[0] + box.l,
            crop[1] + height - box.b,
            crop[0] + box.r,
            crop[1] + height - box.t,
        )
    else:
        raise ValueError("unsupported Docling coordinate origin")
    geometry.display_box(bounds)
    return bounds


def run(request_path: Path, output_path: Path):
    if request_path.stat().st_size > 1024 * 1024:
        raise ValueError("Docling adapter request exceeds limit")
    request = parse_json(request_path.read_bytes())
    if request.get("schema_version") != 1 or request.get("capabilities") != ["prose"]:
        raise ValueError("Docling layout adapter supports only prose evidence")
    config = request.get("configuration")
    if config != {"images_scale": 1.5, "offline": True}:
        raise ValueError("unsupported Docling adapter configuration")
    source = Path(request["source"])
    if source.name != "source.pdf" or digest(source.read_bytes()) != request["source_sha256"]:
        raise ValueError("source identity changed")
    if version("docling") != DOCLING_VERSION:
        raise ValueError("installed Docling revision differs from pinned adapter")
    # Weight files must already be local; no network call is allowed during extraction.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import ConversionStatus, DocumentConverter, PdfFormatOption

    pipeline = PdfPipelineOptions(
        do_ocr=True,
        generate_page_images=True,
        images_scale=1.5,
        enable_remote_services=False,
    )
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)},
    )
    result = converter.convert(source)
    if result.status != ConversionStatus.SUCCESS:
        raise ValueError("Docling did not finish the complete PDF")
    document = result.document
    pages = {
        row["geometry"]["page"]: (
            PageGeometry.model_validate(row["geometry"]),
            row["classification"],
        )
        for row in request["pages"]
    }
    images = {}
    page_images = {}
    records = []
    section = ""
    for item, _ in document.iterate_items():
        label = getattr(getattr(item, "label", None), "value", "")
        content = getattr(item, "text", "")
        if label in ("title", "section_header") and content.strip():
            section = content.strip()[:256]
        if label not in ("title", "section_header", "text", "paragraph", "list_item"):
            continue
        if not content or not content.strip() or not getattr(item, "prov", None):
            continue
        provenance = item.prov[0]
        if provenance.page_no not in pages:
            raise ValueError("Docling evidence references an uninspected page")
        geometry, classification = pages[provenance.page_no]
        if provenance.page_no not in page_images:
            page = document.pages[provenance.page_no]
            if page.image is None or page.image.pil_image is None:
                raise ValueError("Docling page render is unavailable")
            bitmap = page.image.pil_image.convert("RGB")
            if bitmap.width * bitmap.height > 16_000_000:
                raise ValueError("Docling page render exceeds pixel budget")
            buffer = io.BytesIO()
            bitmap.save(buffer, format="PNG")
            png = buffer.getvalue()
            image_hash = digest(png)
            images[image_hash] = png
            page_images[provenance.page_no] = image_hash
        image_hash = page_images[provenance.page_no]
        raw = content.strip()
        text = f"Section: {section}\n\n{raw}" if section and section != raw else raw
        route = classification["action"]
        derivation = (
            "text_layer"
            if route == "retain_text_layer"
            else "ocr"
            if route == "ocr_required"
            else "model_derived"
        )
        record = Evidence(
            source_sha256=request["source_sha256"],
            geometry=geometry,
            bbox=source_box(provenance, geometry),
            page_render_sha256=image_hash,
            extractor=EXTRACTOR,
            revision=REVISION,
            configuration=config,
            raw_output=raw,
            content={"kind": "prose", "text": text},
            derivation=derivation,
            warnings=[] if route != "inspection_required" else ["page_requires_visual_review"],
        )
        records.append(record.model_dump(mode="json"))
        if len(records) > 10000:
            raise ValueError("Docling returned too many evidence regions")
    if not records:
        raise ValueError("Docling returned no grounded prose")
    for image_hash, png in images.items():
        (output_path.parent / f"{image_hash}.png").write_bytes(png)
    output_path.write_bytes(
        canonical(
            {
                "schema_version": 1,
                "source_sha256": request["source_sha256"],
                "adapter_identity": request["adapter_identity"],
                "evidence": records,
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.request, args.output)


if __name__ == "__main__":
    main()
