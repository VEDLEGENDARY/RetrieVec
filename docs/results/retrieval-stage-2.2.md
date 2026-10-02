# Retrieval quality stage 2.2: opt-in extraction, chunks, and stemming

## Decision

Keep the existing upload extraction, paragraph-v1 chunking, and analyzer-v1 as product defaults. The combined alternative improved SciFact nDCG@10 by +0.0477 (paired 95% interval [0.0221, 0.0736]), but SCIDOCS improved by only +0.0039 ([-0.0033, 0.0114]) while p95 worker latency rose from 281.74 to 888.87 ms. The opt-in alternatives also have not passed the PDF evidence gate. No service configuration or private-scope behavior changes in this stage.

## Frozen comparison

The sparse BEIR comparison uses the previously pinned full SciFact and SCIDOCS inputs and their held-out test qrels. Each dataset runs four configurations on identical questions and paper IDs: baseline v1 chunks/analyzer, v1 chunks with English Snowball stemming, paragraph-v2 chunks with v1 analyzer, and both alternatives. BM25 stays at k1=1.2 and b=0.75. Each query retrieves 100 chunks, collapses to papers by first occurrence, and removes query-ID self matches. The report records per-query scores, failures, p50/p95 worker latency, index build time, chunk count, source hashes, snapshot IDs, and 5,000 query-paired bootstrap draws. Worker latency includes local pipe transport but excludes HTTP, authorization, and database work. These are paper-level retrieval metrics, not PDF extraction metrics.

| Dataset | Variant | nDCG@10 | Delta vs baseline, paired 95% interval | p50 / p95 ms | Chunks |
| --- | --- | ---: | ---: | ---: | ---: |
| SciFact | Baseline | 0.5880 | reference | 28.52 / 59.81 | 41,983 |
| SciFact | Snowball | 0.6109 | +0.0228 [0.0023, 0.0449] | 29.45 / 61.21 | 41,983 |
| SciFact | Paragraph-v2 | 0.5923 | +0.0043 [-0.0145, 0.0230] | 33.34 / 79.22 | 50,294 |
| SciFact | Combined | 0.6357 | +0.0477 [0.0221, 0.0736] | 40.70 / 96.15 | 50,294 |
| SCIDOCS | Baseline | 0.1389 | reference | 103.81 / 281.74 | 176,739 |
| SCIDOCS | Snowball | 0.1425 | +0.0035 [-0.0019, 0.0090] | 176.48 / 424.62 | 176,739 |
| SCIDOCS | Paragraph-v2 | 0.1371 | -0.0018 [-0.0077, 0.0039] | 196.98 / 457.35 | 200,821 |
| SCIDOCS | Combined | 0.1429 | +0.0039 [-0.0033, 0.0114] | 376.73 / 888.87 | 200,821 |

The values above are rounded from the [SciFact](sparse-variants-scifact-v1.json) and [SCIDOCS](sparse-variants-scidocs-v1.json) JSON results. Every variant completed its full held-out query set with zero recorded failures. The larger index and much higher latency outweigh the small, uncertain SCIDOCS quality delta; the confidence intervals on both SCIDOCS improvements cross zero. Candidate truncation, chunk-to-paper collapse, and dataset-specific vocabulary can change rankings. The separate original BEIR benchmark also measured dense and hybrid retrieval; this stage isolates sparse changes only. Peak memory was not measured consistently across variants and is not treated as evidence.

## PDF evidence gate

The [PDF evaluation manifest](../../datasets/manifests/pdf-evaluation-v1.json) pins 15 open-access ACL Anthology PDFs by URL and SHA-256. Local pypdf extraction produced a default paragraph-v1 snapshot with 1,571 chunks and an opt-in paragraph-v2 snapshot with 2,008 chunks. The [passage review packet](pdf-passage-review-v1.json) contains 75 candidate passages, five per paper, each tied to a source hash, page range, chunk ID, and passage hash. Its questions and answers remain empty and `quality_evidence` is false. The evaluator refuses to score it until 50–100 passage-linked question/answer pairs have explicit human review, rationale, and consistent provenance. Model-generated drafts were rejected because a local small model produced malformed and unrelated answers.

The PDF snapshots use pypdf plain-text extraction. The optional Docling layout adapter is installed only through the `layout` extra and was not run against this corpus. Some mathematical glyph extraction warned about a missing fontTools CFF font. Therefore this stage has no claim about layout extraction quality, OCR, passage localization, or equation fidelity. BEIR plain text cannot substitute for this PDF review.

## Reproduction

With `retrievald` built and the Python project environment active, run:

```text
python scripts/fetch_pdf_evaluation.py
python -m retrievec import --manifest datasets/manifests/pdf-evaluation-v1.json --source-root artifacts/papers --output artifacts/pdf-eval/snapshots --token-budget 96 --chunker paragraph-v1 --engine artifacts/bin/retrievald.exe
python -m retrievec import --manifest datasets/manifests/pdf-evaluation-v1.json --source-root artifacts/papers --output artifacts/pdf-eval/snapshots --token-budget 96 --chunker paragraph-v2 --overlap 12 --engine artifacts/bin/retrievald.exe
python scripts/compare_sparse_variants.py --dataset scifact --output docs/results/sparse-variants-scifact-v1.json
python scripts/compare_sparse_variants.py --dataset scidocs --output docs/results/sparse-variants-scidocs-v1.json
```

`scripts/evaluate_pdf_variants.py` accepts the reviewed packet and explicit snapshot paths and refuses unreviewed labels. The experimental Go analyzer is versioned `analyzer-v2-snowball-en-0.10.0-unicode-15.0.0` and is selected only by the offline benchmark command.
