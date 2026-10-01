"""Publish measured BEIR tables only from a complete real-model report."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- BEIR RESULTS START -->", "<!-- BEIR RESULTS END -->"


def tables(report):
    if (
        not report.get("complete")
        or not report.get("quality_evidence")
        or report.get("kind") != "full-beir"
        or set(report["datasets"]) != {"scifact", "scidocs"}
    ):
        raise ValueError("only a complete full-corpus real-model report may publish quality tables")
    lines = [
        "| Dataset | Pipeline | nDCG@10 | Recall@100 | MRR@10 | p50 ms | p95 ms |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, dataset in report["datasets"].items():
        for label, run in dataset["runs"].items():
            if run["failures"] or len(run["per_query"]) != dataset["query_count"]:
                raise ValueError("incomplete query accounting")
            metrics, latency = run["metrics"], run["latency_ms"]
            lines.append(
                f"| {name} | {label.replace('_', ' ')} | {metrics['ndcg']:.4f} | "
                f"{metrics['recall']:.4f} | {metrics['mrr']:.4f} | "
                f"{latency['p50']:.2f} | {latency['p95']:.2f} |"
            )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_bytes())
    table = tables(report)
    relative = args.report.resolve().relative_to(ROOT).as_posix()
    command = (
        "python scripts/benchmark_beir.py --phase preflight\n"
        "python scripts/benchmark_beir.py --phase prepare\n"
        "python scripts/benchmark_beir.py --phase tune\n"
        f"python scripts/benchmark_beir.py --phase evaluate --output {relative}\n"
        f"python scripts/render_beir_report.py {relative}"
    )
    limitations = (
        "These are paper-level rankings collapsed from the production top-100 chunk pool, "
        "so fewer than 100 papers can be returned. Latency covers warm local retrieval and "
        "query embedding, excluding HTTP, authentication and database work. SCIDOCS uses "
        "SciFact-selected parameters because it has no training split; no model was trained. "
        "The opt-in lossless wordpiece refinement is recorded in snapshot provenance. "
        "This does not evaluate PDF extraction, answers, private-scope isolation, or concurrency."
    )
    section = (
        f"{START}\n## Measured retrieval results\n\n{table}\n\n"
        f"Source: [{relative}]({relative}). [Protocol and limitations](BENCHMARKS.md).\n\n"
        f"{limitations}\n\nReproduce after installing the documented dependencies and building "
        f"the engine:\n\n```sh\n{command}\n```\n{END}"
    )
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if START in readme:
        before, remainder = readme.split(START, 1)
        _, after = remainder.split(END, 1)
        readme = before + section + after
    else:
        title, remainder = readme.split("\n", 1)
        readme = title + "\n\n" + section + "\n" + remainder
    detail = [
        "# BEIR retrieval benchmark",
        "",
        f"Measured source: [{relative}]({relative}).",
        "",
        table,
        "",
        "## Protocol",
        "",
        limitations,
        "",
        "The grid was committed before held-out evaluation. Development selection uses only "
        "the deterministic SciFact training subset. Dense has no tuned parameters. Sparse and "
        "hybrid select their configurations independently by development nDCG@10. "
        "The JSON retains query IDs, per-query rankings, failures, corpus and input hashes, "
        "model/tokenizer revision and hashes, source hashes, and paired confidence intervals.",
        "",
        "## Build measurements",
        "",
        "| Dataset | Papers | Chunks | Import ms | Embedding ms | "
        "Sparse segment build ms | Warm embedding cache |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for name, dataset in report["datasets"].items():
        p = dataset["prepared"]
        detail.append(
            f"| {name} | {p['papers']} | {p['chunks']} | {p['import_ms']:.2f} | "
            f"{p['embedding_ms']:.2f} | {p['sparse_build_ms']:.2f} | "
            f"{p['warm_embedding_cache']} |"
        )
    detail.extend(
        [
            "",
            "Embedding build times may include reuse from verified per-text caches; "
            "they are not cold-build claims. Sparse queries use the shipped in-memory reference "
            "kernel via an offline pipe, whose startup measurement is recorded separately from "
            "immutable sparse segment construction. Peak memory was not sampled. "
            "Methods run in fixed order, which can affect timing through cache "
            "and thermal effects.",
            "",
            "## Paired bootstrap",
            "",
            "Intervals are descriptive query-paired percentile intervals for right minus left; "
            "they are not corrected for multiple comparisons. Recall uses its declared 100 cutoff; "
            "nDCG and MRR use 10.",
            "",
            "| Dataset | Comparison | Metric | Mean delta | 95% interval | Paired queries |",
            "| --- | --- | --- | ---: | --- | ---: |",
        ]
    )
    for name, dataset in report["datasets"].items():
        for comparison, paired in dataset["paired_bootstrap"].items():
            for metric in ("ndcg", "mrr", "recall"):
                item = paired["metrics"][metric]
                low, high = item["percentile_interval_95"]
                detail.append(
                    f"| {name} | {comparison} | {metric} | "
                    f"{item['mean_delta_right_minus_left']:.4f} | "
                    f"[{low:.4f}, {high:.4f}] | {item['paired_count']} |"
                )
    detail.extend(
        [
            "",
            "## Environment",
            "",
            "```json",
            json.dumps(
                {
                    key: value
                    for key, value in report["environment"].items()
                    if key != "source_sha256"
                },
                indent=2,
            ),
            "```",
            "",
            "## Reproduce",
            "",
            "```sh",
            command,
            "```",
            "",
            "The checksum-verified archives and generated artifacts stay under "
            "ignored `artifacts/`. "
            "Use a new work directory if protocol, model or subset configuration changes. "
            "Windows users can pre-download the official archives with `Invoke-WebRequest` into "
            "`artifacts/beir/downloads/` if Python cannot validate the host certificate chain; "
            "do not disable TLS verification. The runner still verifies the published checksums.",
            "",
            "CI runs a deliberately small real-model subset as a pipeline regression only. "
            "It is never evidence of MiniLM quality or full-corpus speed.",
            "",
        ]
    )
    (ROOT / "BENCHMARKS.md").write_text("\n".join(detail), encoding="utf-8")
    readme_path.write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
