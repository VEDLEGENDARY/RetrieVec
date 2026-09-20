"""Run the synthetic sparse demo against the real executable and save evidence."""

import argparse
import os
import queue
import subprocess
import threading
from pathlib import Path

from benchmark_http import measure
from retrievec.client.capture import capture
from retrievec.client.http import Client
from retrievec.corpus.snapshot import canonical
from retrievec.evaluation.dataset import load_dataset
from retrievec.evaluation.report import evaluate

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--engine",
        type=Path,
        default=ROOT / "artifacts/bin" / ("retrievald.exe" if os.name == "nt" else "retrievald"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("use a new output directory")
    corpus = ROOT / (
        "datasets/fixtures/snapshots/ss_4415a7c573a87a239ee65b0581664ea667b3988e4"
        "be43cb7f3bd069380ee0811"
    )
    dataset_path = ROOT / "datasets/evaluation/synthetic-draft-v1.json"
    dataset = load_dataset(dataset_path, corpus)
    args.output.mkdir(parents=True)
    queries = args.output / "queries.jsonl"
    queries.write_bytes(
        b"".join(
            canonical({k: q[k] for k in ("query_id", "query", "mode")}) + b"\n"
            for q in dataset["queries"]
            if q["split"] == "development"
        )
    )
    process = subprocess.Popen(
        [str(args.engine.resolve()), "--corpus", str(corpus), "--listen", "127.0.0.1:0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    lines = queue.Queue()
    thread = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
    thread.start()
    try:
        line = lines.get(timeout=20).strip()
        if not line.startswith("listening http://"):
            raise RuntimeError("service startup failed")
        client = Client(line.removeprefix("listening "))
        first = capture(client, queries, args.output / "first")
        second = capture(client, queries, args.output / "repeat")
        if first["ranking_sha256"] != second["ranking_sha256"]:
            raise RuntimeError("rankings not reproducible")
        evaluate(args.output / "first", dataset_path, corpus, include_drafts=True)
        for concurrency in (1, 8):
            (args.output / f"latency-{concurrency}.json").write_bytes(
                canonical(measure(client, 100, concurrency)) + b"\n"
            )
        capture(client, ROOT / "datasets/fixtures/queries-v1.jsonl", args.output / "errors")
        print(args.output / "first/report.md")
    finally:
        process.terminate()
        process.communicate(timeout=10)
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
