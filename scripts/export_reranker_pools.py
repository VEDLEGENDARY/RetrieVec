"""Export held-out BEIR hybrid candidate pools without altering the frozen benchmark."""

import argparse
import json
import os
from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest, load_snapshot
from retrievec.dense.model import adapter
from retrievec.evaluation.beir_data import download, order, qrels, rows
from retrievec.evaluation.beir_runtime import Pipeline
from retrievec.registry.artifacts import Store

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("scifact", "scidocs"), required=True)
    parser.add_argument("--work", type=Path, default=ROOT / "artifacts/beir")
    parser.add_argument(
        "--engine",
        type=Path,
        default=ROOT / "artifacts/bin" / ("retrievald.exe" if os.name == "nt" else "retrievald"),
    )
    parser.add_argument("--protocol", type=Path, default=ROOT / "experiments/beir-grid-v1.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0, help="0 evaluates all held-out questions")
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("limit cannot be negative")
    protocol = json.loads(args.protocol.read_bytes())
    selection = json.loads((args.work / "selection.json").read_bytes())
    prepared = json.loads((args.work / args.dataset / "prepared.json").read_bytes())
    if selection["protocol_sha256"] != digest(canonical(protocol)):
        raise ValueError("development selection does not match protocol")
    source = download(args.dataset, args.work / "downloads", protocol["dataset_md5"][args.dataset])
    query_text = {row["_id"]: row["text"] for row in rows(source / "queries.jsonl")}
    judgments = qrels(source / "qrels/test.tsv")
    query_ids = order(list(judgments), protocol["seed"])
    if args.limit:
        query_ids = query_ids[: args.limit]
    store = Store(args.work / args.dataset / "store")
    snapshot_id = prepared["snapshot_id"]
    manifest = store.manifest(snapshot_id)
    corpus = store.path("corpora", manifest["corpus_snapshot_id"], "ss_")
    _, _, chunks = load_snapshot(corpus)
    by_id = {item["chunk_id"]: item for item in chunks}
    pipeline = Pipeline(
        args.engine,
        args.work / args.dataset,
        prepared,
        adapter("minilm"),
        max(100, protocol["candidate_chunks"]),
    )
    pools = []
    config = selection["selected"]["hybrid"]
    try:
        for index, query_id in enumerate(query_ids, 1):
            query = query_text[query_id]
            sparse, _ = pipeline.sparse(query, config)
            dense, _ = pipeline.dense(query)
            hits, _ = pipeline.hybrid(sparse, dense, config["rrf_k"])
            candidates = []
            for hit in hits[:100]:
                chunk = by_id[hit["chunk_id"]]
                candidates.append(
                    {
                        "chunk_id": chunk["chunk_id"],
                        "paper_id": chunk["paper_id"],
                        "text": chunk["text"],
                    }
                )
            pools.append({"query_id": query_id, "query": query, "candidates": candidates})
            if index % 25 == 0:
                print(f"Exported {index}/{len(query_ids)}", flush=True)
    finally:
        pipeline.close()
    result = {
        "schema_version": 1,
        "retrieval": "hybrid",
        "scope": "public_benchmark_pinned_snapshot",
        "dataset": args.dataset,
        "snapshot_id": snapshot_id,
        "corpus_snapshot_id": manifest["corpus_snapshot_id"],
        "protocol_sha256": digest(canonical(protocol)),
        "qrels_sha256": digest((source / "qrels/test.tsv").read_bytes()),
        "judgment_provenance": "beir_qrels",
        "judgment_unit": "paper_id",
        "subset": bool(args.limit),
        "judgments": {key: judgments[key] for key in query_ids},
        "pools": pools,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(result) + b"\n")


if __name__ == "__main__":
    main()
