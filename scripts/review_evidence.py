"""Publish explicit human review decisions as a new immutable evidence bundle."""

import argparse
from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest, parse_json
from retrievec.extraction.schema import Evidence, Review
from retrievec.extraction.store import EvidenceStore
from retrievec.registry.worker import publish_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle")
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    args = parser.parse_args()
    if args.decisions.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("review decisions exceed limit")
    decisions = parse_json(args.decisions.read_bytes())
    if not isinstance(decisions, list) or not 1 <= len(decisions) <= 10000:
        raise ValueError("provide explicit review decisions")
    by_id = {}
    for row in decisions:
        if not isinstance(row, dict) or set(row) - {"evidence_id", "review", "content"}:
            raise ValueError("invalid review decision fields")
        key = row["evidence_id"]
        review = Review.model_validate(row["review"])
        if key in by_id or review.status == "pending":
            raise ValueError("duplicate or unfinished review decision")
        by_id[key] = row
    store = EvidenceStore(args.store)
    bundle, objects = store.bundle(args.bundle)
    if set(by_id) - {item.identity for item in objects}:
        raise ValueError("review refers to an object outside this bundle")
    revised, lineage, images = [], [], {}
    for item in objects:
        original_id = item.identity
        if original_id in by_id:
            decision = by_id[original_id]
            item = Evidence.model_validate(
                {
                    **item.model_dump(mode="json"),
                    "review": decision["review"],
                    "content": decision.get("content", item.content.model_dump(mode="json")),
                }
            )
            lineage.append(
                {
                    "original_evidence_id": original_id,
                    "revised_evidence_id": item.identity,
                    "review": item.review.model_dump(mode="json"),
                }
            )
        revised.append(item)
        for key in (item.page_render_sha256, item.region_crop_sha256):
            if key is not None and key not in images:
                path = store.image(key)
                if (
                    path.is_symlink()
                    or not path.resolve().is_relative_to(store.root)
                    or path.stat().st_size > 32 * 1024 * 1024
                ):
                    raise ValueError("invalid retained image")
                images[key] = path.read_bytes()
                if sum(map(len, images.values())) > 128 * 1024 * 1024:
                    raise ValueError("review bundle image budget exceeded")
    source_path = store.root / "evidence-sources" / (bundle["source_sha256"] + ".pdf")
    if (
        source_path.is_symlink()
        or not source_path.resolve().is_relative_to(store.root)
        or source_path.stat().st_size > 64 * 1024 * 1024
    ):
        raise ValueError("invalid retained original")
    source = source_path.read_bytes()
    if digest(source) != bundle["source_sha256"]:
        raise ValueError("retained original changed")
    published = store.publish(source, revised, images)
    record = {
        "schema_version": 1,
        "original_bundle": args.bundle,
        "revised_bundle": published,
        "decisions": lineage,
    }
    raw = canonical(record)
    target = store.root / "evidence-reviews" / (digest(raw) + ".json")
    if not target.resolve().is_relative_to(store.root):
        raise ValueError("review record escapes store")
    publish_bytes(target, raw + b"\n")
    print(published)


if __name__ == "__main__":
    main()
