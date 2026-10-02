"""Compare opt-in chunking and stemming on identical held-out BEIR questions.

This is a sparse-only experiment. PDF extraction quality requires the separate
human-reviewed PDF passage packet and must not be inferred from BEIR text.
"""

import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path

from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import import_manifest
from retrievec.corpus.section_chunks import sections
from retrievec.corpus.snapshot import canonical, digest, load_snapshot
from retrievec.corpus.wordpieces import WordpieceBudget
from retrievec.dense.model import adapter
from retrievec.evaluation.beir_data import qrels, rows
from retrievec.evaluation.beir_eval import score
from retrievec.evaluation.load import percentile
from retrievec.evaluation.paired import compare

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("baseline", "stemmed", "paragraph", "combined")


def preflight_paragraph_sources(manifest_path, source_root):
    """Fail fast on title/heading layouts that would yield no indexable body."""
    manifest = json.loads(manifest_path.read_bytes())
    failures = []
    for record in manifest["sources"]:
        text = (source_root / record["path"]).read_text(encoding="utf-8")
        found, _ = sections(text)
        if not any(any(character.isalnum() for character in body) for _, body in found):
            failures.append(record["paper_id"])
    if failures:
        raise ValueError(
            f"paragraph-v2 has no tokens for {len(failures)} sources: {failures[:5]}"
        )


def report(worker, name, query_rows, judgments, chunk_papers, *, limit=0):
    first = json.loads(worker.stdout.readline())
    if "snapshot_id" not in first or "analyzer_version" not in first:
        raise ValueError("benchmark worker did not report its corpus and analyzer")
    outcomes, failures = [], []
    queries = {item["_id"]: item["text"] for item in query_rows}
    ids = sorted(set(queries) & set(judgments))
    if limit:
        ids = ids[:limit]
    if not ids:
        raise ValueError("no held-out queries")
    worker.stdin.write(
        json.dumps({"query": "retrieval", "top_k": 100, "k1": 1.2, "b": 0.75}) + "\n"
    )
    worker.stdin.flush()
    json.loads(worker.stdout.readline())  # fixed warmup, not scored
    for qid in ids:
        try:
            worker.stdin.write(
                json.dumps({"query": queries[qid], "top_k": 100, "k1": 1.2, "b": 0.75})
                + "\n"
            )
            worker.stdin.flush()
            result = json.loads(worker.stdout.readline())
            seen, ranking = {qid}, []
            for hit in result["hits"]:
                paper = chunk_papers[hit["chunk_id"]]
                if paper not in seen:
                    seen.add(paper)
                    ranking.append(paper)
            outcomes.append(
                {
                    "query_id": qid,
                    **score(ranking, judgments[qid]),
                    "elapsed_ms": result["elapsed_ms"],
                    "ranking": ranking,
                }
            )
        except (KeyError, ValueError, BrokenPipeError, OSError) as error:
            failures.append({"query_id": qid, "error": type(error).__name__})
    times = [item["elapsed_ms"] for item in outcomes]
    return {
        "schema_version": 1,
        "dataset_id": name,
        "split": "test",
        "cutoff": 10,
        "includes_drafts": False,
        "per_query": outcomes,
        "failures": failures,
        "missing_queries": [],
        "results_sha256": digest(canonical(outcomes)),
        "metrics": {
            metric: statistics.mean(row[metric] for row in outcomes)
            if outcomes
            else None
            for metric in ("ndcg", "mrr", "recall", "coverage")
        },
        "latency_ms": {"p50": percentile(times, 0.5), "p95": percentile(times, 0.95)},
        "worker": first,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("scifact", "scidocs"), required=True)
    parser.add_argument(
        "--engine", type=Path, default=ROOT / "artifacts/bin/retrievald.exe"
    )
    parser.add_argument("--work", type=Path, default=ROOT / "artifacts/beir")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--queries", type=int, default=0, help="smoke subset; 0 runs all"
    )
    parser.add_argument(
        "--paragraph-snapshot", type=Path, help="reuse a pinned v2 corpus"
    )
    args = parser.parse_args()
    if args.queries < 0:
        parser.error("--queries must be nonnegative")
    dataset = args.work / args.dataset
    source = args.work / "downloads" / args.dataset
    prepared = json.loads((dataset / "prepared.json").read_bytes())
    baseline = Path(prepared["corpus"])
    manifest, baseline_papers, _ = load_snapshot(baseline)
    if manifest["collection_id"] != args.dataset or prepared["subset"]:
        raise ValueError("expected the full frozen BEIR corpus")
    for filename, expected in prepared["inputs"].items():
        if digest((source / filename).read_bytes()) != expected:
            raise ValueError("BEIR source changed")
    query_rows = rows(source / "queries.jsonl")
    judgments = qrels(source / "qrels/test.tsv")
    alternate = args.work / "sparse-variants" / args.dataset
    alternate.mkdir(parents=True, exist_ok=True)
    reference_analyzer = GoAnalyzer(args.engine)
    reference_analyzer.analyze([])
    stemmed_version = reference_analyzer.version.replace(
        "analyzer-v1-unicode-", "analyzer-v2-snowball-en-0.10.0-unicode-", 1
    )
    if args.paragraph_snapshot:
        paragraph = args.paragraph_snapshot
    else:
        model = adapter("minilm")
        preflight_paragraph_sources(dataset / "sources.json", dataset / "sources")
        paragraph = import_manifest(
            dataset / "sources.json",
            dataset / "sources",
            alternate / "corpora",
            args.dataset,
            32,
            GoAnalyzer(args.engine),
            wordpiece_budget=WordpieceBudget(model, GoAnalyzer(args.engine)),
            chunker="paragraph-v2",
            overlap=8,
        )
    paragraph_manifest, paragraph_papers, _ = load_snapshot(paragraph)
    if not paragraph_manifest["configuration"]["chunker_version"].startswith(
        "paragraph-v2-32-"
    ) or {p["paper_id"]: p["source_sha256"] for p in paragraph_papers} != {
        p["paper_id"]: p["source_sha256"] for p in baseline_papers
    }:
        raise ValueError("paragraph corpus does not match the baseline sources")
    snapshots = {
        "baseline": baseline,
        "stemmed": baseline,
        "paragraph": paragraph,
        "combined": paragraph,
    }
    result = {
        "schema_version": 1,
        "dataset": args.dataset,
        "source_sha256": prepared["inputs"],
        "qrels_sha256": digest((source / "qrels/test.tsv").read_bytes()),
        "query_limit": args.queries,
        "quality_evidence": args.queries == 0,
        "variants": {},
    }
    for variant in VARIANTS:
        corpus = snapshots[variant]
        snapshot, _, chunks = load_snapshot(corpus)
        analyzer = stemmed_version if variant in ("stemmed", "combined") else None
        command = [
            str(args.engine.resolve()),
            "benchmark",
            "--corpus",
            str(corpus.resolve()),
        ]
        if analyzer:
            command += ["--analyzer", analyzer]
        started = time.perf_counter()
        with (alternate / f"{variant}.stderr.log").open(
            "w", encoding="utf-8"
        ) as errors:
            worker = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
            try:
                measured = report(
                    worker,
                    args.dataset,
                    query_rows,
                    judgments,
                    {chunk["chunk_id"]: chunk["paper_id"] for chunk in chunks},
                    limit=args.queries,
                )
                measured["wall_ms"] = (time.perf_counter() - started) * 1000
                measured["corpus_snapshot_id"] = snapshot["snapshot_id"]
                measured["chunk_count"] = len(chunks)
                result["variants"][variant] = measured
            finally:
                worker.terminate()
                worker.communicate(timeout=30)
        print(f"{variant}: {measured['metrics']['ndcg']:.4f} nDCG@10", flush=True)
    baseline_report = result["variants"]["baseline"]
    result["paired"] = {
        variant: compare(
            baseline_report, result["variants"][variant], samples=5000, seed=1729
        )
        for variant in VARIANTS[1:]
    }
    result["decision"] = (
        "No default change; review paired quality, cost, and PDF judgments first."
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_bytes(canonical(result) + b"\n")
    temporary.replace(args.output)


if __name__ == "__main__":
    main()
