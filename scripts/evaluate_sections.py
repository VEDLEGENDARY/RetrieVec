"""Untuned section-boundary BM25 comparison on complete BEIR test splits."""

import argparse
import json
import statistics
import subprocess
from pathlib import Path

from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import chunk_page
from retrievec.corpus.sections import segments
from retrievec.corpus.snapshot import canonical, digest, make_chunk, make_paper, publish_snapshot
from retrievec.evaluation.beir_data import qrels, rows
from retrievec.evaluation.beir_eval import score
from retrievec.evaluation.paired import compare


def build(data, work, engine):
    analyzer = GoAnalyzer(engine)
    analyzer.analyze([])
    records = rows(data / "corpus.jsonl")
    papers, variants = [], {"plain": [], "section_aware": []}
    identified = 0
    for start in range(0, len(records), 32):
        batch = records[start : start + 32]
        texts = [r.get("title", "") + "\n\n" + r.get("text", "") for r in batch]
        tokenized = analyzer.analyze(texts)
        for row, text, tokens in zip(batch, texts, tokenized, strict=True):
            paper = make_paper(
                paper_id=row["_id"],
                title=row.get("title") or row["_id"],
                authors=[],
                source=text.encode(),
                source_url=None,
                extraction_version="beir-title-abstract-v1",
                license_note="BEIR dataset terms; no original full paper",
            )
            papers.append(paper)
            spans, _, _ = segments(text)
            identified += any(label != "unclassified" for _, _, label, _ in spans)
            parts = {"plain": chunk_page(text, tokens, 96), "section_aware": []}
            for begin, end, _, _ in spans:
                local = [
                    {
                        **t,
                        "start": t["start"] - len(text[:begin].encode()),
                        "end": t["end"] - len(text[:begin].encode()),
                    }
                    for t in tokens
                    if len(text[:begin].encode()) <= t["start"]
                    and t["end"] <= len(text[:end].encode())
                ]
                parts["section_aware"].extend(chunk_page(text[begin:end], local, 96))
            for variant, packed in parts.items():
                if "".join(packed) != text:
                    raise ValueError("section chunker lost text")
                version = f"paragraph-v1-96-{analyzer.version}"
                if variant == "section_aware":
                    version += "-explicit-sections-v1"
                variants[variant].extend(
                    make_chunk(paper, part, i, "section-study", version)
                    for i, part in enumerate(packed)
                )
        if start % 1024 == 0:
            print(f"preparing {data.name}: {start}/{len(records)}", flush=True)
    return (
        {
            name: publish_snapshot(
                work / "corpora",
                papers,
                chunks,
                "section-study",
                {"token_budget": 96, "section_aware": name != "plain"},
            )
            for name, chunks in variants.items()
        },
        variants,
        identified,
    )


def measure(engine, corpus, chunks, queries, judgments, name):
    mapping = {c["chunk_id"]: c["paper_id"] for c in chunks}
    report = {
        "schema_version": 1,
        "dataset_id": name,
        "split": "test",
        "cutoff": 10,
        "includes_drafts": False,
        "per_query": [],
        "failures": [],
        "missing_queries": [],
    }
    process = subprocess.Popen(
        [str(engine.resolve()), "benchmark", "--corpus", str(corpus)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    try:
        json.loads(process.stdout.readline())
        for i, qid in enumerate(sorted(judgments), 1):
            process.stdin.write(
                json.dumps({"query": queries[qid], "top_k": 100, "k1": 1.2, "b": 0.75}) + "\n"
            )
            process.stdin.flush()
            result = json.loads(process.stdout.readline())
            ranking, seen = [], {qid}
            for hit in result["hits"]:
                paper = mapping[hit["chunk_id"]]
                if paper not in seen:
                    seen.add(paper)
                    ranking.append(paper)
            report["per_query"].append(
                {"query_id": qid, "ranking": ranking, **score(ranking, judgments[qid])}
            )
            if i % 100 == 0:
                print(f"{name}/{corpus.name}: {i}/{len(judgments)}", flush=True)
    finally:
        process.terminate()
        process.communicate(timeout=15)
    report["results_sha256"] = digest(canonical(report["per_query"]))
    report["mean"] = {
        metric: statistics.mean(r[metric] for r in report["per_query"])
        for metric in ("ndcg", "mrr", "recall", "coverage")
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="BEIR download directory")
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "schema_version": 1,
        "complete": False,
        "defaults_changed": False,
        "configuration": {
            "token_budget": 96,
            "wordpiece_refinement": False,
            "k1": 1.2,
            "b": 0.75,
            "candidate_chunks": 100,
            "tuning": "none",
        },
        "scope": "Product paragraph packer with explicit section boundaries; sparse only.",
        "limitations": "Abstract-only evaluation; dense/hybrid and full papers unmeasured.",
        "datasets": {},
    }
    for name in ("scifact", "scidocs"):
        data = args.data / name
        paths, variants, identified = build(data, args.work / name, args.engine)
        queries = {r["_id"]: r["text"] for r in rows(data / "queries.jsonl")}
        judgments = qrels(data / "qrels/test.tsv")
        measured = {
            variant: measure(args.engine, path, variants[variant], queries, judgments, name)
            for variant, path in paths.items()
        }
        result["datasets"][name] = {
            "input_sha256": digest((data / "corpus.jsonl").read_bytes()),
            "records_with_explicit_headings": identified,
            "runs": measured,
            "paired": compare(measured["plain"], measured["section_aware"]),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    result["complete"] = True
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
