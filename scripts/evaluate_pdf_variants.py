"""Run the sparse PDF comparison only after passage questions are human-reviewed.

This reports paper-level retrieval. Passage localization and extraction fidelity
remain separate review dimensions; a paper hit alone does not prove support.
"""

import argparse
import json
import subprocess
import time
from pathlib import Path

from compare_sparse_variants import report
from prepare_pdf_review import validate_review
from retrievec.corpus.snapshot import canonical, digest, load_snapshot
from retrievec.evaluation.paired import compare

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packet", type=Path, default=ROOT / "docs/results/pdf-passage-review-v1.json"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "datasets/manifests/pdf-evaluation-v1.json",
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--paragraph", type=Path, required=True)
    parser.add_argument("--layout", type=Path, help="optional independently pinned layout snapshot")
    parser.add_argument("--engine", type=Path, default=ROOT / "artifacts/bin/retrievald.exe")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_bytes())
    validate_review(packet, args.manifest, args.baseline)
    questions = [
        {"_id": item["candidate_id"], "text": item["question"]} for item in packet["candidates"]
    ]
    judgments = {item["candidate_id"]: {item["paper_id"]: 1} for item in packet["candidates"]}
    if len(judgments) != len(questions):
        raise ValueError("duplicate PDF question identity")
    snapshots = {"baseline": args.baseline, "paragraph": args.paragraph}
    if args.layout:
        snapshots["layout"] = args.layout
    result = {
        "schema_version": 1,
        "kind": "reviewed-pdf-paper-retrieval",
        "packet_sha256": digest(args.packet.read_bytes()),
        "manifest_sha256": digest(args.manifest.read_bytes()),
        "question_count": len(questions),
        "metric_limit": (
            "Paper-level relevance only; extraction and passage support need separate human review."
        ),
        "variants": {},
    }
    for name, path in snapshots.items():
        manifest, papers, chunks = load_snapshot(path)
        if {paper["paper_id"] for paper in papers} != {
            item["paper_id"] for item in packet["candidates"]
        }:
            raise ValueError(f"{name} does not cover the identical paper set")
        command = [
            str(args.engine.resolve()),
            "benchmark",
            "--corpus",
            str(path.resolve()),
        ]
        started = time.perf_counter()
        with subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        ) as worker:
            measured = report(
                worker,
                "pdf-evaluation-v1",
                questions,
                judgments,
                {chunk["chunk_id"]: chunk["paper_id"] for chunk in chunks},
            )
            worker.terminate()
            worker.communicate(timeout=30)
        measured["wall_ms"] = (time.perf_counter() - started) * 1000
        measured["corpus_snapshot_id"] = manifest["snapshot_id"]
        measured["chunk_count"] = len(chunks)
        result["variants"][name] = measured
    baseline = result["variants"]["baseline"]
    result["paired"] = {
        name: compare(baseline, value, samples=5000, seed=1729)
        for name, value in result["variants"].items()
        if name != "baseline"
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_bytes(canonical(result) + b"\n")
    temporary.replace(args.output)


if __name__ == "__main__":
    main()
