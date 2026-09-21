"""Typed evidence and raster images resolve only through an authorized pinned chunk."""

from typing import Literal

from fastapi import Request
from fastapi.responses import Response

from retrievec.app.auth import principal
from retrievec.app.errors import APIError
from retrievec.corpus.snapshot import digest, load_snapshot
from retrievec.registry.artifacts import Store


def install_evidence(app):
    registry = app.state.registry
    store = Store(app.state.settings.store)

    def resolve(user, collection_id, snapshot_id, chunk_id):
        from retrievec.extraction.indexing import EvidenceIndex

        registered = registry.resolve(user, collection_id, snapshot_id)
        corpus, papers, chunks = load_snapshot(
            store.path("corpora", registered["corpus_snapshot_id"], "ss_")
        )
        chunk = next((item for item in chunks if item["chunk_id"] == chunk_id), None)
        if chunk is None:
            raise APIError(404, "evidence_unavailable", "Evidence is not in this snapshot")
        index = EvidenceIndex(store.root, corpus)
        item = index.object_for(chunk)
        if item is None:
            raise APIError(404, "evidence_unavailable", "No retained visual region is available")
        paper = next(row for row in papers if row["paper_version_id"] == chunk["paper_version_id"])
        if item.source_sha256 != paper["source_sha256"]:
            raise APIError(409, "evidence_unavailable", "Evidence source identity differs")
        return item, index.store

    route = "/api/v1/collections/{collection_id}/snapshots/{snapshot_id}/evidence/{chunk_id}"

    @app.get(route)
    def inspect(collection_id: str, snapshot_id: str, chunk_id: str, request: Request):
        user = principal(request)
        item, _ = resolve(user, collection_id, snapshot_id, chunk_id)
        registry.resolve(user, collection_id, snapshot_id)
        return {
            "evidence_id": item.identity,
            "locator": item.locator(),
            "content": item.content.model_dump(mode="json"),
            "derivation": item.derivation,
            "review": item.review.model_dump(),
            "warnings": item.warnings,
            "confidence": item.confidence,
            "raw_output": item.raw_output,
            "extractor": item.extractor,
            "revision": item.revision,
            "synthesis_allowed": item.synthesis_allowed,
        }

    @app.get(route + "/images/{kind}")
    def image(
        collection_id: str,
        snapshot_id: str,
        chunk_id: str,
        kind: Literal["page", "crop"],
        request: Request,
    ):
        from retrievec.extraction.store import validate_png

        user = principal(request)
        item, evidence_store = resolve(user, collection_id, snapshot_id, chunk_id)
        checksum = item.page_render_sha256 if kind == "page" else item.region_crop_sha256
        if checksum is None:
            raise APIError(404, "image_unavailable", "This region has no separate crop")
        path = evidence_store.image(checksum)
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(store.root)
            or path.stat().st_size > 32 * 1024 * 1024
        ):
            raise APIError(409, "image_unavailable", "Retained image is unavailable")
        raw = path.read_bytes()
        if digest(raw) != checksum:
            raise APIError(409, "image_unavailable", "Retained image is inconsistent")
        validate_png(raw)
        registry.resolve(user, collection_id, snapshot_id)
        return Response(
            raw,
            media_type="image/png",
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )

    @app.get(route + "/original")
    def original(collection_id: str, snapshot_id: str, chunk_id: str, request: Request):
        user = principal(request)
        item, _ = resolve(user, collection_id, snapshot_id, chunk_id)
        path = store.root / "evidence-sources" / (item.source_sha256 + ".pdf")
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(store.root)
            or path.stat().st_size > 64 * 1024 * 1024
        ):
            raise APIError(409, "source_unavailable", "Retained original is unavailable")
        raw = path.read_bytes()
        if digest(raw) != item.source_sha256:
            raise APIError(409, "source_unavailable", "Retained original is inconsistent")
        registry.resolve(user, collection_id, snapshot_id)
        return Response(
            raw,
            media_type="application/pdf",
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": 'inline; filename="source.pdf"',
            },
        )
