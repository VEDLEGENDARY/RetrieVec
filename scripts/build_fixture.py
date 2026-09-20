"""Rebuild the committed synthetic corpus snapshot from its small source fixture."""

from pathlib import Path

from retrievec.corpus.snapshot import make_chunk, make_paper, parse_json, publish_snapshot

ROOT = Path(__file__).resolve().parents[1]


def records() -> tuple[list[dict], list[dict]]:
    sources = parse_json((ROOT / "datasets/fixtures/synthetic_sources.json").read_bytes())
    papers, chunks = [], []
    for source in sources:
        paper = make_paper(
            paper_id=source["paper_id"],
            title=source["title"],
            authors=[],
            source=source["text"].encode("utf-8"),
            source_url=None,
            extraction_version="synthetic-text-v1",
            license_note="Original synthetic fixture; MIT",
        )
        papers.append(paper)
        chunks.append(make_chunk(paper, source["text"], 0, "synthetic", "whole-document-v1"))
    return papers, chunks


if __name__ == "__main__":
    papers, chunks = records()
    print(
        publish_snapshot(
            ROOT / "datasets/fixtures/snapshots",
            papers,
            chunks,
            "synthetic",
            {"fixture_version": 1},
        )
    )
