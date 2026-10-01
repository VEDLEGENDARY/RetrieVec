"""Reproducible BEIR benchmark through shipped import, embeddings, BM25 and RRF."""

import argparse
import json
import os
import platform
import subprocess
import time
from pathlib import Path

# Bound BLAS before importing numpy through retrieval modules.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "2")

from retrievec.corpus.snapshot import canonical, digest  # noqa: E402
from retrievec.dense.model import adapter  # noqa: E402
from retrievec.evaluation.beir_data import download, order, prepare, qrels, rows  # noqa: E402
from retrievec.evaluation.beir_eval import evaluate, tune  # noqa: E402
from retrievec.evaluation.beir_runtime import Pipeline  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase", choices=("preflight", "prepare", "tune", "evaluate", "all"), default="all"
    )
    parser.add_argument("--work", type=Path, default=ROOT / "artifacts/beir")
    parser.add_argument(
        "--engine",
        type=Path,
        default=ROOT / "artifacts/bin" / ("retrievald.exe" if os.name == "nt" else "retrievald"),
    )
    parser.add_argument("--protocol", type=Path, default=ROOT / "experiments/beir-grid-v1.json")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/results/benchmark-2026-10-01.json"
    )
    parser.add_argument("--documents", type=int, default=0, help="smoke subset only, 0 = complete")
    parser.add_argument("--queries", type=int, default=0, help="smoke subset only, 0 = complete")
    parser.add_argument("--embedding", choices=("minilm", "fixture"), default="minilm")
    args = parser.parse_args()
    if min(args.documents, args.queries) < 0 or bool(args.documents) != bool(args.queries):
        parser.error("subset requires both positive --documents and --queries")
    if args.embedding == "fixture" and not args.documents:
        parser.error("fixture embeddings are permitted only in explicit smoke subsets")
    relative = args.protocol.resolve().relative_to(ROOT).as_posix()
    frozen = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=ROOT)
    protocol = json.loads(args.protocol.read_bytes())
    if json.loads(frozen) != protocol:
        parser.error("commit the protocol before running the benchmark")
    args.work.mkdir(parents=True, exist_ok=True)
    model = adapter(args.embedding)
    original_encode = model.encode
    progress = {"count": 0, "last": 0.0}

    def encode(texts):
        value = original_encode(texts)
        progress["count"] += len(texts)
        if time.monotonic() - progress["last"] > 30:
            print(f"Encoded {progress['count']} inputs", flush=True)
            progress["last"] = time.monotonic()
        return value

    model.encode = encode
    prepared, data, queries = {}, {}, {}
    for name in protocol["datasets"]:
        print(f"Loading {name}", flush=True)
        data[name] = download(name, args.work / "downloads", protocol["dataset_md5"][name])
        query_rows = rows(data[name] / "queries.jsonl")
        queries[name] = {row["_id"]: row["text"] for row in query_rows}
        if len(queries[name]) != len(query_rows):
            raise ValueError("duplicate query identity")
        work = args.work / name
        metadata = work / "prepared.json"
        if args.phase == "preflight":
            prepare(name, data[name], work, args.engine, model, protocol, args.documents, True)
            continue
        if metadata.exists():
            prepared[name] = json.loads(metadata.read_bytes())
            if (
                prepared[name]["protocol_sha256"] != digest(canonical(protocol))
                or prepared[name]["model"] != model.config
                or prepared[name].get("document_limit") != args.documents
            ):
                raise ValueError(
                    "prepared artifact configuration differs; use a new work directory"
                )
            for file, expected in prepared[name]["inputs"].items():
                if digest((data[name] / file).read_bytes()) != expected:
                    raise ValueError("dataset changed since preparation")
        elif args.phase in ("prepare", "all"):
            prepared[name] = prepare(
                name, data[name], work, args.engine, model, protocol, args.documents
            )
        else:
            raise ValueError("run prepare first")
    if args.phase in ("preflight", "prepare"):
        return
    selection_path = args.work / "selection.json"
    if not selection_path.exists():
        if args.phase not in ("tune", "all"):
            raise ValueError("freeze development selection before evaluation")
        training = qrels(data["scifact"] / "qrels/train.tsv")
        test_ids = set(qrels(data["scifact"] / "qrels/test.tsv"))
        if set(training) & test_ids:
            raise ValueError("train/test query identity leakage")
        ids = order(list(training), protocol["seed"])[: len(training) // 2]
        if args.queries:
            ids = ids[: args.queries]
        pipeline = Pipeline(
            args.engine,
            args.work / "scifact",
            prepared["scifact"],
            model,
            protocol["candidate_chunks"],
        )
        try:
            selection = tune(pipeline, queries["scifact"], training, ids, protocol)
        finally:
            pipeline.close()
        selection.update(
            {
                "protocol_sha256": digest(canonical(protocol)),
                "train_qrels_sha256": digest((data["scifact"] / "qrels/train.tsv").read_bytes()),
                "subset": bool(args.documents),
                "document_limit": args.documents,
                "query_limit": args.queries,
            }
        )
        save(selection_path, selection)
        print("Development selection frozen", flush=True)
    selection = json.loads(selection_path.read_bytes())
    if (
        selection["protocol_sha256"] != digest(canonical(protocol))
        or selection.get("document_limit") != args.documents
        or selection.get("query_limit") != args.queries
    ):
        raise ValueError("selection configuration differs")
    if selection["train_qrels_sha256"] != digest(
        (data["scifact"] / "qrels/train.tsv").read_bytes()
    ):
        raise ValueError("training judgments changed")
    if args.phase == "tune":
        return
    result = {
        "schema_version": 1,
        "kind": "smoke-subset" if args.documents else "full-beir",
        "quality_evidence": False,
        "complete": False,
        "protocol": protocol,
        "selection": selection,
        "environment": {
            "platform": platform.platform(),
            "cpu": platform.processor(),
            "logical_cpus": os.cpu_count(),
            "python": platform.python_version(),
            "git_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "engine_sha256": digest(args.engine.read_bytes()),
            "source_sha256": {
                str(path.relative_to(ROOT).as_posix()): digest(path.read_bytes())
                for path in sorted(
                    [
                        *ROOT.glob("python/src/retrievec/**/*.py"),
                        *ROOT.glob("engine/**/*.go"),
                        Path(__file__).resolve(),
                    ]
                )
            },
            "tracked_diff_sha256": digest(
                subprocess.check_output(
                    ["git", "diff", "HEAD", "--", "python", "engine", "scripts"], cwd=ROOT
                )
            ),
            "peak_memory": None,
            "memory_note": "Not sampled; do not infer memory efficiency",
        },
        "datasets": {},
    }
    for name in protocol["datasets"]:
        judgments = qrels(data[name] / "qrels/test.tsv")
        ids = order(list(judgments), protocol["seed"])
        if args.queries:
            ids = ids[: args.queries]
        pipeline = Pipeline(
            args.engine, args.work / name, prepared[name], model, protocol["candidate_chunks"]
        )
        try:
            report = evaluate(pipeline, name, queries[name], judgments, ids, protocol, selection)
        finally:
            pipeline.close()
        report["prepared"] = prepared[name]
        report["sparse_worker_startup"] = pipeline.startup
        report["qrels_sha256"] = digest((data[name] / "qrels/test.tsv").read_bytes())
        report["query_count"] = len(ids)
        result["datasets"][name] = report
        save(args.output, result)
    result["complete"] = not any(
        run["failures"]
        for dataset in result["datasets"].values()
        for run in dataset["runs"].values()
    )
    result["quality_evidence"] = (
        result["complete"] and args.embedding == "minilm" and not args.documents
    )
    save(args.output, result)
    print(args.output, flush=True)


if __name__ == "__main__":
    main()
