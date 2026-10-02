"""Select passage-linked questions for owner review; never invent reviewed labels."""

import argparse
import json
from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest, load_snapshot, parse_json


def prepare(manifest_path: Path, snapshot_path: Path) -> dict:
    sources = parse_json(manifest_path.read_bytes())["sources"]
    manifest, papers, chunks = load_snapshot(snapshot_path)
    by_source = {paper["paper_id"]: paper for paper in papers}
    if len(sources) != 15 or len(by_source) != 15:
        raise ValueError("PDF review packet requires 15 distinct papers")
    by_paper = {source["paper_id"]: [] for source in sources}
    for chunk in chunks:
        by_paper[chunk["paper_id"]].append(chunk)
    candidates = []
    for source in sorted(sources, key=lambda item: item["paper_id"]):
        paper_id = source["paper_id"]
        paper = by_source[paper_id]
        if paper["source_sha256"] != source["source_sha256"]:
            raise ValueError("PDF review source differs from pinned manifest")
        passages = sorted(
            (
                chunk
                for chunk in by_paper[paper_id]
                if chunk["page_range"] is not None and len(chunk["text"].split()) >= 20
            ),
            key=lambda chunk: (chunk["page_range"][0], chunk["ordinal"]),
        )
        # Avoid the final fifth, which is often references or appendices.
        passages = passages[: max(5, len(passages) * 4 // 5)]
        if len(passages) < 5:
            raise ValueError(f"too few passage candidates for {paper_id}")
        selected = [passages[(len(passages) - 1) * i // 5] for i in range(1, 6)]
        for chunk in selected:
            candidates.append(
                {
                    "candidate_id": "pq_"
                    + digest(
                        canonical(
                            {
                                "snapshot": manifest["snapshot_id"],
                                "chunk": chunk["chunk_id"],
                            }
                        )
                    ),
                    "paper_id": paper_id,
                    "paper_title": paper["title"],
                    "source_sha256": paper["source_sha256"],
                    "chunk_id": chunk["chunk_id"],
                    "text_sha256": chunk["text_sha256"],
                    "page_range": chunk["page_range"],
                    "passage": chunk["text"],
                    "question": "",
                    "expected_answer": "",
                    "review_status": "pending",
                    "reviewer": None,
                    "review_rationale": "",
                }
            )
    if len(candidates) != 75 or len({item["chunk_id"] for item in candidates}) != 75:
        raise ValueError("PDF review selection is incomplete or duplicated")
    return {
        "schema_version": 1,
        "kind": "pdf-passage-review-packet",
        "manifest_sha256": digest(manifest_path.read_bytes()),
        "corpus_snapshot_id": manifest["snapshot_id"],
        "question_count": 0,
        "quality_evidence": False,
        "candidates": candidates,
    }


def validate_review(packet: dict, manifest_path: Path, snapshot_path: Path) -> None:
    if packet.get("kind") != "pdf-passage-review-packet" or packet.get("quality_evidence"):
        raise ValueError("invalid PDF review packet")
    snapshot, papers, chunks = load_snapshot(snapshot_path)
    if (
        packet.get("manifest_sha256") != digest(manifest_path.read_bytes())
        or packet.get("corpus_snapshot_id") != snapshot["snapshot_id"]
    ):
        raise ValueError("PDF review packet corpus provenance differs")
    by_chunk = {item["chunk_id"]: item for item in chunks}
    by_paper = {item["paper_id"]: item for item in papers}
    candidates = packet.get("candidates")
    if not isinstance(candidates, list) or not 50 <= len(candidates) <= 100:
        raise ValueError("PDF review requires 50-100 passage-linked questions")
    if packet.get("question_count") != len(candidates):
        raise ValueError("PDF review question count differs from reviewed candidates")
    if len({item["candidate_id"] for item in candidates}) != len(candidates):
        raise ValueError("duplicate PDF review candidate")
    for item in candidates:
        chunk = by_chunk.get(item["chunk_id"])
        paper = by_paper.get(item["paper_id"])
        if (
            chunk is None
            or paper is None
            or chunk["paper_id"] != item["paper_id"]
            or chunk["text_sha256"] != item["text_sha256"]
            or chunk["text"] != item["passage"]
            or chunk["page_range"] != item["page_range"]
            or paper["source_sha256"] != item["source_sha256"]
            or paper["title"] != item["paper_title"]
            or item["candidate_id"]
            != "pq_"
            + digest(canonical({"snapshot": snapshot["snapshot_id"], "chunk": chunk["chunk_id"]}))
        ):
            raise ValueError("PDF review passage provenance differs")
        if not item["question"].strip() or not item["expected_answer"].strip():
            raise ValueError("question and expected answer require owner review")
        if (
            item["review_status"] != "reviewed"
            or not item["reviewer"]
            or not item["review_rationale"].strip()
        ):
            raise ValueError("human review is incomplete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("datasets/manifests/pdf-evaluation-v1.json"),
    )
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet = prepare(args.manifest, args.snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"{len(packet['candidates'])} passages queued for human question review")


if __name__ == "__main__":
    main()
