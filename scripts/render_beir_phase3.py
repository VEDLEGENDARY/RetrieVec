"""Render phase-three measurements while retaining the historical baseline."""

import json

START = "<!-- PHASE3 RESULTS START -->"
END = "<!-- PHASE3 RESULTS END -->"


def render(root, report, relative, table):
    lines = [
        START,
        "# Phase 3 retrieval controls",
        "",
        f"Measured source: [{relative}]({relative}). Product ranking defaults unchanged.",
        "",
        table,
        "",
        "All corpora are complete BEIR title-and-abstract records. Matched full-paper text "
        "is unavailable; no whole-paper result is claimed. Document BM25 uses one title plus "
        "abstract per document. Chunk runs collapse the top 100 chunks to unique papers, "
        "so they can return fewer than 100 papers. Query-ID self matches are excluded.",
        "",
        "Warm local latency excludes model startup, HTTP, authorization and database work. "
        "Sequential/concurrent hybrid runs alternate order and measure actual wall time. "
        "Fusion and cross-encoder totals are component sums using shared measured retrieval "
        "plus incremental scoring, not independently measured end-to-end requests. "
        "No concurrent-user load test is represented by these numbers.",
        "",
        "## Concurrent scheduling",
        "",
    ]
    for name, dataset in report["datasets"].items():
        item = dataset["paired_latency"]
        low, high = item["percentile_interval_95"]
        parity = sum(
            row.get("parity") is True for row in dataset["runs"]["concurrent_hybrid"]["per_query"]
        )
        lines.append(
            f"- {name}: exact sparse, dense and fused ranking/score parity for {parity} queries; "
            f"mean concurrent minus sequential latency "
            f"{item['mean_delta_ms_concurrent_minus_sequential']:+.2f} ms "
            f"(query-paired 95% interval [{low:+.2f}, {high:+.2f}] ms)."
        )
    lines += [
        "",
        "## Paired quality comparisons",
        "",
        "Right minus left; 5,000 seeded query-paired bootstrap samples. Intervals are "
        "descriptive and not corrected for multiple comparisons. Full recall and MRR "
        "intervals are retained in the JSON.",
        "",
        "| Dataset | Comparison | nDCG@10 delta | 95% interval | Paired queries |",
        "| --- | --- | ---: | --- | ---: |",
    ]
    for name, dataset in report["datasets"].items():
        for label, paired in dataset["paired_bootstrap"].items():
            item = paired["metrics"]["ndcg"]
            low, high = item["percentile_interval_95"]
            lines.append(
                f"| {name} | {label} | {item['mean_delta_right_minus_left']:+.4f} | "
                f"[{low:+.4f}, {high:+.4f}] | {item['paired_count']} |"
            )
    lines += [
        "",
        "## Analyzer and chunk controls",
        "",
        "The shipped analyzer lowercases Unicode letter/digit runs, without stemming or "
        "stopword removal. Offline English controls isolate an explicit stopword list and "
        "Snowball stemming. They do not reproduce Elasticsearch/Lucene byte for byte: "
        "BEIR indexes title and body as separate language-analyzed fields and uses "
        "best-fields matching with a 0.5 tie breaker; this control concatenates them. "
        "Document scoring changes document-frequency and length statistics as well as "
        "eliminating chunk collapse; its effect cannot be attributed to collapse alone. "
        "See the [official BEIR BM25 implementation]"
        "(https://github.com/beir-cellar/beir/blob/main/"
        "beir/retrieval/search/lexical/elastic_search.py) "
        "for the external baseline's implementation context.",
        "",
        "Legacy dense/fusion runs use 32-token chunks with lossless wordpiece refinement. "
        "Exact product controls use the web upload's 96-token budget and importer's "
        "256-token budget without refinement. Sparse runs preserve these exact chunks. "
        "Dense/hybrid controls that exceed the pinned encoder limit are unavailable, "
        "not silently truncated or re-chunked.",
        "",
        "| Dataset | Product chunker | Chunks | Encoder overflows |",
        "| --- | --- | ---: | ---: |",
    ]
    for name, dataset in report["datasets"].items():
        for label, metadata in dataset["product_chunk_preflight"].items():
            lines.append(
                f"| {name} | {label} | {metadata['chunks']} | {metadata.get('overflow_count', 0)} |"
            )
    reranker = report["reranker"]
    lines += [
        "",
        "## Cross-encoder diagnosis",
        "",
        f"Model `{reranker['model']}`, model revision `{reranker['revision']}`, "
        f"tokenizer revision `{reranker['tokenizer_revision']}`; maximum "
        f"{reranker['max_tokens']} wordpieces per query/passage pair. Both title and "
        "passage text are supplied. The frozen first 50 hybrid chunks are reordered, "
        "then the unchanged tail is appended before paper collapse. "
        "`enabled_by_default=False`. Score blending was not run in this phase's frozen "
        "protocol; no blend improvement is claimed.",
        "",
    ]
    for name, dataset in report["datasets"].items():
        rows = dataset["runs"]["cross_encoder_top50"]["per_query"]
        lines.append(
            f"- {name}: {sum(row['truncated_candidates'] for row in rows)} truncated candidates; "
            f"largest pair {max(row['maximum_pair_wordpieces'] for row in rows)} wordpieces."
        )
    lines += [
        "",
        "## Development selection and rejected alternatives",
        "",
        "Only the original frozen SciFact development IDs select fusion weights. "
        "Selected weights transfer unchanged to SCIDOCS. No test-query tuning or "
        "global quality-default promotion is performed.",
        "",
        "| Family | Sparse weight | Development nDCG@10 | Decision |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in report["selection"]["grid_scores"]:
        config = row["configuration"]
        decision = "Selected for evaluation" if row["selected"] else "Rejected on development"
        lines.append(
            f"| {config['family']} | {config['sparse_weight']} | {row['ndcg']:.4f} | {decision} |"
        )
    lines += [
        "",
        "## Reproduce",
        "",
        "Use the README native environment and complete baseline BEIR artifacts first. "
        "Use a new work directory if source, protocol or model hashes change.",
        "",
        "```sh",
        "python scripts/benchmark_beir.py --study phase3 --phase tune",
        f"python scripts/benchmark_beir.py --study phase3 --phase evaluate --output {relative}",
        f"python scripts/render_beir_report.py {relative}",
        "```",
        "",
        "Source hashes, corpus hashes, per-query rankings, frozen pool hashes and model "
        "artifact hashes are recorded in the result. These are retrieval judgments, "
        "not an answer-quality or human-review study. NLI was NOT run.",
        "",
        "```json",
        json.dumps(
            {key: value for key, value in report["environment"].items() if key != "source_sha256"},
            indent=2,
        ),
        "```",
        END,
        "",
    ]
    path = root / "BENCHMARKS.md"
    previous = path.read_text(encoding="utf-8")
    if START in previous:
        previous = previous.split(END, 1)[1].lstrip()
    path.write_text("\n".join(lines) + "\n" + previous, encoding="utf-8")
