"""Publish measured BEIR tables only from a complete real-model report."""

import argparse
import json
from pathlib import Path

from retrievec.evaluation.report_io import load_report

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
    for name in ("scifact", "scidocs"):
        dataset = report["datasets"][name]
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


def readme_summary(report):
    tables(report)  # Reject incomplete or fabricated publication accounting first.
    label = "concurrent_hybrid" if report.get("study") == "phase3" else "default_hybrid"
    lines = ["| Corpus | Hybrid nDCG@10 | Warm retrieval p50 |", "|---|---:|---:|"]
    for name, title in (("scifact", "SciFact"), ("scidocs", "SCIDOCS")):
        run = report["datasets"][name]["runs"][label]
        lines.append(
            f"| {title} | {run['metrics']['ndcg']:.4f} | {run['latency_ms']['p50']:.2f} ms |"
        )
    return "\n".join(lines)


def update_readme(root, report, relative):
    section = (
        f"{START}\n\n{readme_summary(report)}\n\n"
        f"Source: [{relative}]({relative}). Warm local retrieval excludes HTTP, "
        f"authorization and database work.\n\n{END}"
    )
    path = root / "README.md"
    before, rest = path.read_text(encoding="utf-8").split(START, 1)
    _, after = rest.split(END, 1)
    path.write_text(before + section + after, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = load_report(args.report)
    table = tables(report)
    relative = args.report.resolve().relative_to(ROOT).as_posix()
    update_readme(ROOT, report, relative)
    if report.get("study") == "phase3":
        from render_beir_phase3 import render

        render(ROOT, report, relative, table)
        return
    raw_relative = relative.removesuffix(".gz")
    command = (
        "python scripts/benchmark_beir.py --phase preflight\n"
        "python scripts/benchmark_beir.py --phase prepare\n"
        "python scripts/benchmark_beir.py --phase tune\n"
        f"python scripts/benchmark_beir.py --phase evaluate --output {raw_relative}\n"
        f"python scripts/render_beir_report.py {raw_relative}"
    )
    limitations = (
        "These are paper-level rankings collapsed from the production top-100 chunk pool, "
        "so fewer than 100 papers can be returned. Latency covers warm local retrieval and "
        "query embedding, excluding HTTP, authentication and database work. SCIDOCS uses "
        "SciFact-selected parameters because it has no training split; no model was trained. "
        "The benchmark's opt-in lossless wordpiece refinement differs from the product's "
        "default PDF upload chunking and is recorded in snapshot provenance. "
        "This does not evaluate PDF extraction, answers, private-scope isolation, or concurrency."
    )
    effects = {}
    for name in ("scifact", "scidocs"):
        effects[name] = report["datasets"][name]["paired_bootstrap"][
            "default_hybrid_vs_tuned_hybrid"
        ]["metrics"]["ndcg"]
    selected = report["selection"]["selected"]
    findings = [
        "## Decision",
        "",
        "The SciFact development split selected hybrid "
        f"`k1={selected['hybrid']['k1']}`, `b={selected['hybrid']['b']}`, "
        f"`rrf_k={selected['hybrid']['rrf_k']}`. Sparse selection retained "
        f"`k1={selected['sparse']['k1']}`, `b={selected['sparse']['b']}`.",
        "",
    ]
    for name in ("scifact", "scidocs"):
        effect = effects[name]
        low, high = effect["percentile_interval_95"]
        findings.append(
            f"Tuned minus unchanged hybrid nDCG@10 on {name}: "
            f"{effect['mean_delta_right_minus_left']:+.4f} "
            f"(paired 95% interval [{low:+.4f}, {high:+.4f}]; "
            f"{effect['paired_count']} queries)."
        )
    findings.append("")
    if (
        effects["scifact"]["percentile_interval_95"][0] > 0
        and effects["scidocs"]["percentile_interval_95"][1] < 0
    ):
        findings.append(
            "The transfer reverses direction across the two tasks. Reject the SciFact-tuned "
            "hybrid configuration as a global default. Keep product defaults unchanged; "
            "consider a scope-specific change only after representative application-corpus "
            "evaluation and owner review."
        )
    else:
        findings.append(
            "The two tasks do not establish a consistent quality gain. Keep product defaults "
            "unchanged pending representative application-corpus evaluation and owner review."
        )
    detail = [
        "# BEIR retrieval benchmark",
        "",
        f"Measured source: [{relative}]({relative}).",
        "",
        table,
        "",
        *findings,
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
        "SciFact development and test questions search the same SciFact corpus. "
        "Query-ID overlap is rejected, but paraphrase-level leakage and near-duplicate "
        "paper versions were not audited; "
        "these results do not establish broader-domain generalization.",
        "",
        "## Build measurements",
        "",
        "| Dataset | Papers | Chunks | Import ms | Embedding ms | "
        "Sparse segment build ms | Warm embedding cache |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for name in ("scifact", "scidocs"):
        dataset = report["datasets"][name]
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
    for name in ("scifact", "scidocs"):
        dataset = report["datasets"][name]
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
            "Complete the [native setup](docs/DEVELOPMENT.md#native-setup) first. "
            "Replace `python` with "
            "`.\\.venv\\Scripts\\python.exe` on Windows or `.venv/bin/python` on Linux.",
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
            "```powershell",
            "New-Item -ItemType Directory -Force artifacts/beir/downloads | Out-Null",
            "Invoke-WebRequest -Uri "
            "'https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip' "
            "-OutFile artifacts/beir/downloads/scifact.zip",
            "Invoke-WebRequest -Uri "
            "'https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scidocs.zip' "
            "-OutFile artifacts/beir/downloads/scidocs.zip",
            "```",
            "",
            "CI runs a deliberately small real-model subset as a pipeline regression only. "
            "It is never evidence of MiniLM quality or full-corpus speed.",
            "",
        ]
    )
    (ROOT / "BENCHMARKS.md").write_text("\n".join(detail), encoding="utf-8")


if __name__ == "__main__":
    main()
