"""Render phase-three measurements while retaining the historical baseline."""

import json
import statistics

START = "<!-- PHASE3 RESULTS START -->"
END = "<!-- PHASE3 RESULTS END -->"


def render(root, report, relative, table):
    raw_relative = relative.removesuffix(".gz")
    lines = [
        START,
        "# BEIR retrieval benchmark",
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
        *report.get("measurement_notes", []),
        "",
        "## Concurrent scheduling",
        "",
        *(
            [
                "The measured parity and paired latency evidence enable bounded concurrent "
                "scheduling by default. Ranking, analyzer, chunking and reranker defaults "
                "are preserved.",
                "",
            ]
            if report.get("post_measurement_decision", {}).get("concurrent_legs_enabled_by_default")
            else []
        ),
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
        "The [BEIR paper, sections 4–5](https://arxiv.org/abs/2104.08663) reports BM25 "
        "nDCG@10 of 0.665 on SciFact and 0.158 on SCIDOCS using Anserini/Lucene "
        "with k1=0.9 and b=0.4 and separate title/passage fields. These published "
        "reference values are not new measurements or exact replicas of this control, "
        "which retains RetrieVec's k1=1.2 and b=0.75.",
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
    lines += ["", "Measured decomposition of the sparse comparison:", ""]
    for name, dataset in report["datasets"].items():
        runs = dataset["runs"]
        sparse = runs["default_sparse"]
        document = runs["document_bm25_unicode"]
        stemmed = runs["document_bm25_snowball_english"]
        papers = statistics.mean(len(row["ranking"]) for row in sparse["per_query"])
        document_papers = statistics.mean(len(row["ranking"]) for row in document["per_query"])
        lines.append(
            f"- {name}: chunk-collapsed sparse nDCG@10 {sparse['metrics']['ndcg']:.4f}; "
            f"whole-record Unicode BM25 {document['metrics']['ndcg']:.4f}; "
            f"whole-record stemmed BM25 {stemmed['metrics']['ndcg']:.4f}. "
            f"The top-100 chunk pool yields a mean {papers:.1f} unique papers, "
            f"versus {document_papers:.1f} for the document control. "
            "The paired intervals above quantify these differences; they do not "
            "establish an implementation bug or justify changing product defaults."
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
    lines += ["", "Held-out decisions (no quality defaults promoted):", ""]
    for variant in ("weighted_rrf", "normalized_score", "sparse_then_dense", "cross_encoder_top50"):
        effects = {
            name: dataset["paired_bootstrap"]["default_hybrid_vs_" + variant]["metrics"]["ndcg"]
            for name, dataset in report["datasets"].items()
        }
        losses = [name for name, item in effects.items() if item["percentile_interval_95"][1] < 0]
        if losses:
            decision = "Reject as a global default: paired degradation on " + ", ".join(losses)
        elif all(item["mean_delta_right_minus_left"] == 0 for item in effects.values()):
            decision = "Selected weights reproduce the baseline ordering; no quality change"
        else:
            decision = "Retain as an opt-in control; these tasks do not establish broad superiority"
        lines.append(f"- {variant}: {decision}.")
    lines += [
        "",
        "## Reproduce",
        "",
        "Use the README native environment and complete baseline BEIR artifacts first. "
        "Use a new work directory if source, protocol or model hashes change.",
        "",
        "```sh",
        "python scripts/benchmark_beir.py --study phase3 --phase tune "
        "--work artifacts/beir-phase3-reproduction",
        "python scripts/benchmark_beir.py --study phase3 --phase evaluate "
        f"--work artifacts/beir-phase3-reproduction --output {raw_relative}",
        f"python scripts/render_beir_report.py {raw_relative}",
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
    if previous.startswith("# BEIR retrieval benchmark"):
        previous = previous.replace(
            "# BEIR retrieval benchmark", "## Historical baseline (2026-10-01)", 1
        )
    path.write_text("\n".join(lines) + "\n" + previous, encoding="utf-8")
