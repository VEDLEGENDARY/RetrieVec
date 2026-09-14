"""Verify a local import against source text, page provenance, and token budgets."""

import argparse
import json
from pathlib import Path

from retrievallab.corpus.analyzer import GoAnalyzer
from retrievallab.corpus.importer import extract_pages
from retrievallab.corpus.snapshot import digest, load_snapshot, parse_json


def audit(snapshot: Path, source_manifest: Path, source_root: Path) -> dict:
    manifest, papers, chunks = load_snapshot(snapshot)
    sources = parse_json(source_manifest.read_bytes())["sources"]
    by_id = {paper["paper_id"]: paper for paper in papers}
    analyzer = GoAnalyzer()
    summary = []
    for source in sources:
        path = source_root / source["path"]
        raw = path.read_bytes()
        if digest(raw) != source["source_sha256"]:
            raise ValueError("source hash changed")
        extraction_version, pages = extract_pages(path, raw)
        if by_id[source["paper_id"]]["extraction_version"] != extraction_version:
            raise ValueError("extractor version changed")
        paper_chunks = sorted(
            (chunk for chunk in chunks if chunk["paper_id"] == source["paper_id"]),
            key=lambda chunk: chunk["ordinal"],
        )
        counts = []
        for start in range(0, len(paper_chunks), 128):
            batch = analyzer.analyze([chunk["text"] for chunk in paper_chunks[start : start + 128]])
            counts.extend(len(tokens) for tokens in batch)
        if any(not 0 < count <= manifest["configuration"]["token_budget"] for count in counts):
            raise ValueError("chunk token budget violated")
        skipped_pages = []
        for page, text in pages:
            page_chunks = [
                chunk
                for chunk in paper_chunks
                if chunk["page_range"] == (None if page is None else [page, page])
            ]
            if not page_chunks:
                if analyzer.analyze([text])[0]:
                    raise ValueError("indexable page lost")
                skipped_pages.append(page)
            elif "".join(chunk["text"] for chunk in page_chunks) != text:
                raise ValueError("chunk text has gaps or overlap")
        summary.append(
            {
                "paper_id": source["paper_id"],
                "pages": len(pages),
                "chunks": len(paper_chunks),
                "tokens": sum(counts),
                "max_chunk_tokens": max(counts),
                "skipped_pages": skipped_pages,
            }
        )
    return {
        "snapshot_id": manifest["snapshot_id"],
        "analyzer_version": analyzer.version,
        "configuration": manifest["configuration"],
        "papers": summary,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.snapshot, args.manifest, args.source_root), indent=2))
