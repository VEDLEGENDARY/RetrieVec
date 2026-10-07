<!-- PHASE3 RESULTS START -->
# BEIR retrieval benchmark

Measured source: [docs/results/benchmark-2026-10-05-phase3.json.gz](docs/results/benchmark-2026-10-05-phase3.json.gz). Product ranking defaults unchanged.

| Dataset | Pipeline | nDCG@10 | Recall@100 | MRR@10 | p50 ms | p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| scifact | concurrent hybrid | 0.6670 | 0.9487 | 0.6299 | 255.35 | 360.21 |
| scifact | cross encoder top50 | 0.7105 | 0.9487 | 0.6806 | 2763.09 | 3410.40 |
| scifact | default dense | 0.6735 | 0.9283 | 0.6337 | 257.53 | 369.52 |
| scifact | default hybrid | 0.6670 | 0.9487 | 0.6299 | 347.79 | 486.09 |
| scifact | default sparse | 0.5880 | 0.8489 | 0.5514 | 82.85 | 191.48 |
| scifact | document bm25 english stopwords | 0.6645 | 0.8859 | 0.6326 | 2.73 | 10.45 |
| scifact | document bm25 english stopwords snowball | 0.6889 | 0.9209 | 0.6531 | 3.29 | 7.92 |
| scifact | document bm25 snowball english | 0.6868 | 0.9247 | 0.6530 | 8.81 | 25.42 |
| scifact | document bm25 unicode | 0.6617 | 0.8859 | 0.6276 | 8.52 | 22.83 |
| scifact | importer default sparse | 0.6542 | 0.8786 | 0.6217 | 12.22 | 25.98 |
| scifact | normalized score | 0.6796 | 0.9527 | 0.6438 | 255.29 | 360.05 |
| scifact | sparse then dense | 0.6639 | 0.8489 | 0.6297 | 106.83 | 216.02 |
| scifact | web default sparse | 0.6190 | 0.8739 | 0.5824 | 25.19 | 49.97 |
| scifact | weighted rrf | 0.6670 | 0.9487 | 0.6299 | 255.19 | 359.89 |
| scidocs | concurrent hybrid | 0.1928 | 0.3997 | 0.3326 | 897.29 | 1097.51 |
| scidocs | cross encoder top50 | 0.1700 | 0.3997 | 0.2945 | 2487.92 | 3181.07 |
| scidocs | default dense | 0.2128 | 0.4313 | 0.3553 | 953.45 | 1110.07 |
| scidocs | default hybrid | 0.1928 | 0.3997 | 0.3326 | 1125.10 | 1690.79 |
| scidocs | default sparse | 0.1389 | 0.2967 | 0.2506 | 226.48 | 651.90 |
| scidocs | document bm25 english stopwords | 0.1540 | 0.3497 | 0.2759 | 9.92 | 25.96 |
| scidocs | document bm25 english stopwords snowball | 0.1572 | 0.3602 | 0.2754 | 13.09 | 32.10 |
| scidocs | document bm25 snowball english | 0.1554 | 0.3573 | 0.2714 | 40.88 | 78.28 |
| scidocs | document bm25 unicode | 0.1523 | 0.3473 | 0.2719 | 39.10 | 78.47 |
| scidocs | importer default sparse | 0.1512 | 0.3429 | 0.2681 | 47.74 | 94.88 |
| scidocs | normalized score | 0.1947 | 0.4054 | 0.3320 | 897.36 | 1089.89 |
| scidocs | sparse then dense | 0.1981 | 0.2967 | 0.3457 | 241.72 | 624.32 |
| scidocs | web default sparse | 0.1416 | 0.3133 | 0.2493 | 95.94 | 193.27 |
| scidocs | weighted rrf | 0.1928 | 0.3997 | 0.3326 | 897.07 | 1089.49 |

All corpora are complete BEIR title-and-abstract records. Matched full-paper text is unavailable; no whole-paper result is claimed. Document BM25 uses one title plus abstract per document. Chunk runs collapse the top 100 chunks to unique papers, so they can return fewer than 100 papers. Query-ID self matches are excluded.

Warm local latency excludes model startup, HTTP, authorization and database work. Sequential/concurrent hybrid runs alternate order and measure actual wall time. Fusion and cross-encoder totals are component sums using shared measured retrieval plus incremental scoring, not independently measured end-to-end requests. No concurrent-user load test is represented by these numbers.

The measurement resumed from 172 SciFact checkpoints, then from 725 SCIDOCS checkpoints after the offline sparse worker exceeded its 30-second deadline. All completed observations are retained without outlier filtering. Timings span sessions and are descriptive local observations, not controlled release benchmarks.

## Concurrent scheduling

The measured parity and paired latency evidence enable bounded concurrent scheduling by default. Ranking, analyzer, chunking and reranker defaults are preserved.

- scidocs: exact sparse, dense and fused ranking/score parity for 1000 queries; mean concurrent minus sequential latency -297.41 ms (query-paired 95% interval [-312.21, -283.24] ms).
- scifact: exact sparse, dense and fused ranking/score parity for 300 queries; mean concurrent minus sequential latency -93.41 ms (query-paired 95% interval [-101.16, -85.76] ms).

## Paired quality comparisons

Right minus left; 5,000 seeded query-paired bootstrap samples. Intervals are descriptive and not corrected for multiple comparisons. Full recall and MRR intervals are retained in the JSON.

| Dataset | Comparison | nDCG@10 delta | 95% interval | Paired queries |
| --- | --- | ---: | --- | ---: |
| scidocs | default_hybrid_vs_concurrent_hybrid | +0.0000 | [+0.0000, +0.0000] | 1000 |
| scidocs | default_hybrid_vs_cross_encoder_top50 | -0.0228 | [-0.0303, -0.0151] | 1000 |
| scidocs | default_hybrid_vs_document_bm25_english_stopwords | -0.0388 | [-0.0464, -0.0309] | 1000 |
| scidocs | default_hybrid_vs_document_bm25_english_stopwords_snowball | -0.0357 | [-0.0444, -0.0269] | 1000 |
| scidocs | default_hybrid_vs_document_bm25_snowball_english | -0.0374 | [-0.0462, -0.0284] | 1000 |
| scidocs | default_hybrid_vs_document_bm25_unicode | -0.0405 | [-0.0482, -0.0326] | 1000 |
| scidocs | default_hybrid_vs_importer_default_sparse | -0.0417 | [-0.0494, -0.0339] | 1000 |
| scidocs | default_hybrid_vs_normalized_score | +0.0019 | [-0.0021, +0.0060] | 1000 |
| scidocs | default_hybrid_vs_sparse_then_dense | +0.0052 | [+0.0002, +0.0102] | 1000 |
| scidocs | default_hybrid_vs_web_default_sparse | -0.0512 | [-0.0585, -0.0441] | 1000 |
| scidocs | default_hybrid_vs_weighted_rrf | +0.0000 | [+0.0000, +0.0000] | 1000 |
| scidocs | default_sparse_vs_document_bm25_unicode | +0.0134 | [+0.0066, +0.0204] | 1000 |
| scidocs | document_bm25_unicode_vs_english_stopwords | +0.0017 | [+0.0002, +0.0032] | 1000 |
| scidocs | document_bm25_unicode_vs_english_stopwords_snowball | +0.0048 | [-0.0005, +0.0105] | 1000 |
| scidocs | document_bm25_unicode_vs_snowball_english | +0.0031 | [-0.0023, +0.0088] | 1000 |
| scifact | default_hybrid_vs_concurrent_hybrid | +0.0000 | [+0.0000, +0.0000] | 300 |
| scifact | default_hybrid_vs_cross_encoder_top50 | +0.0435 | [+0.0172, +0.0709] | 300 |
| scifact | default_hybrid_vs_document_bm25_english_stopwords | -0.0024 | [-0.0311, +0.0274] | 300 |
| scifact | default_hybrid_vs_document_bm25_english_stopwords_snowball | +0.0219 | [-0.0069, +0.0514] | 300 |
| scifact | default_hybrid_vs_document_bm25_snowball_english | +0.0198 | [-0.0082, +0.0481] | 300 |
| scifact | default_hybrid_vs_document_bm25_unicode | -0.0053 | [-0.0335, +0.0236] | 300 |
| scifact | default_hybrid_vs_importer_default_sparse | -0.0127 | [-0.0426, +0.0163] | 300 |
| scifact | default_hybrid_vs_normalized_score | +0.0127 | [-0.0011, +0.0266] | 300 |
| scifact | default_hybrid_vs_sparse_then_dense | -0.0030 | [-0.0227, +0.0173] | 300 |
| scifact | default_hybrid_vs_web_default_sparse | -0.0479 | [-0.0765, -0.0197] | 300 |
| scifact | default_hybrid_vs_weighted_rrf | +0.0000 | [+0.0000, +0.0000] | 300 |
| scifact | default_sparse_vs_document_bm25_unicode | +0.0736 | [+0.0470, +0.1002] | 300 |
| scifact | document_bm25_unicode_vs_english_stopwords | +0.0029 | [-0.0028, +0.0091] | 300 |
| scifact | document_bm25_unicode_vs_english_stopwords_snowball | +0.0272 | [+0.0096, +0.0465] | 300 |
| scifact | document_bm25_unicode_vs_snowball_english | +0.0251 | [+0.0066, +0.0449] | 300 |

## Analyzer and chunk controls

The [BEIR paper, sections 4–5](https://arxiv.org/abs/2104.08663) reports BM25 nDCG@10 of 0.665 on SciFact and 0.158 on SCIDOCS using Anserini/Lucene with k1=0.9 and b=0.4 and separate title/passage fields. These published reference values are not new measurements or exact replicas of this control, which retains RetrieVec's k1=1.2 and b=0.75.

The shipped analyzer lowercases Unicode letter/digit runs, without stemming or stopword removal. Offline English controls isolate an explicit stopword list and Snowball stemming. They do not reproduce Elasticsearch/Lucene byte for byte: BEIR indexes title and body as separate language-analyzed fields and uses best-fields matching with a 0.5 tie breaker; this control concatenates them. Document scoring changes document-frequency and length statistics as well as eliminating chunk collapse; its effect cannot be attributed to collapse alone. See the [official BEIR BM25 implementation](https://github.com/beir-cellar/beir/blob/main/beir/retrieval/search/lexical/elastic_search.py) for the external baseline's implementation context.

Legacy dense/fusion runs use 32-token chunks with lossless wordpiece refinement. Exact product controls use the web upload's 96-token budget and importer's 256-token budget without refinement. Sparse runs preserve these exact chunks. Dense/hybrid controls that exceed the pinned encoder limit are unavailable, not silently truncated or re-chunked.

| Dataset | Product chunker | Chunks | Encoder overflows |
| --- | --- | ---: | ---: |
| scidocs | importer_default | 31691 | 8565 |
| scidocs | web_default | 81985 | 87 |
| scifact | importer_default | 8224 | 3800 |
| scifact | web_default | 19041 | 5 |

Measured decomposition of the sparse comparison:

- scidocs: chunk-collapsed sparse nDCG@10 0.1389; whole-record Unicode BM25 0.1523; whole-record stemmed BM25 0.1554. The top-100 chunk pool yields a mean 80.3 unique papers, versus 100.0 for the document control. The paired intervals above quantify these differences; they do not establish an implementation bug or justify changing product defaults.
- scifact: chunk-collapsed sparse nDCG@10 0.5880; whole-record Unicode BM25 0.6617; whole-record stemmed BM25 0.6868. The top-100 chunk pool yields a mean 75.8 unique papers, versus 100.0 for the document control. The paired intervals above quantify these differences; they do not establish an implementation bug or justify changing product defaults.

## Cross-encoder diagnosis

Model `cross-encoder/ms-marco-MiniLM-L6-v2`, model revision `9cc09816f0a7a8aaceefa40a3cfbb843c1bfa579`, tokenizer revision `9cc09816f0a7a8aaceefa40a3cfbb843c1bfa579`; maximum 512 wordpieces per query/passage pair. Both title and passage text are supplied. The frozen first 50 hybrid chunks are reordered, then the unchanged tail is appended before paper collapse. `enabled_by_default=False`. Score blending was not run in this phase's frozen protocol; no blend improvement is claimed.

- scidocs: 0 truncated candidates; largest pair 256 wordpieces.
- scifact: 0 truncated candidates; largest pair 175 wordpieces.

## Development selection and rejected alternatives

Only the original frozen SciFact development IDs select fusion weights. Selected weights transfer unchanged to SCIDOCS. No test-query tuning or global quality-default promotion is performed.

| Family | Sparse weight | Development nDCG@10 | Decision |
| --- | ---: | ---: | --- |
| weighted_rrf | 0.25 | 0.6708 | Rejected on development |
| weighted_rrf | 0.5 | 0.6713 | Selected for evaluation |
| weighted_rrf | 0.75 | 0.6490 | Rejected on development |
| normalized_score | 0.25 | 0.6738 | Rejected on development |
| normalized_score | 0.5 | 0.6865 | Selected for evaluation |
| normalized_score | 0.75 | 0.6300 | Rejected on development |

Held-out decisions (no quality defaults promoted):

- weighted_rrf: Selected weights reproduce the baseline ordering; no quality change.
- normalized_score: Retain as an opt-in control; these tasks do not establish broad superiority.
- sparse_then_dense: Retain as an opt-in control; these tasks do not establish broad superiority.
- cross_encoder_top50: Reject as a global default: paired degradation on scidocs.

## Reproduce

Use the README native environment and complete baseline BEIR artifacts first. Use a new work directory if source, protocol or model hashes change.

```sh
python scripts/benchmark_beir.py --study phase3 --phase tune --work artifacts/beir-phase3-reproduction
python scripts/benchmark_beir.py --study phase3 --phase evaluate --work artifacts/beir-phase3-reproduction --output docs/results/benchmark-2026-10-05-phase3.json
python scripts/render_beir_report.py docs/results/benchmark-2026-10-05-phase3.json
```

Source hashes, corpus hashes, per-query rankings, frozen pool hashes and model artifact hashes are recorded in the result. These are retrieval judgments, not an answer-quality or human-review study. NLI was NOT run.

```json
{
  "engine_sha256": "85f0437aae5e8a9592e251cb81849f234bce7c467b061f09de1153d898226066",
  "git_commit": "b1c04818373279dae4b7166c457032fd7bd76c6a",
  "platform": "Windows-11-10.0.26200-SP0",
  "processor": "Intel64 Family 6 Model 170 Stepping 4, GenuineIntel",
  "python": "3.13.15",
  "threads": {
    "OMP_NUM_THREADS": "2",
    "OPENBLAS_NUM_THREADS": "1"
  }
}
```
<!-- PHASE3 RESULTS END -->

## Historical baseline (2026-10-01)

Measured source: [docs/results/benchmark-2026-10-01.json.gz](docs/results/benchmark-2026-10-01.json.gz).

| Dataset | Pipeline | nDCG@10 | Recall@100 | MRR@10 | p50 ms | p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| scifact | default dense | 0.6735 | 0.9283 | 0.6337 | 265.59 | 293.07 |
| scifact | default hybrid | 0.6670 | 0.9487 | 0.6299 | 375.84 | 485.07 |
| scifact | default sparse | 0.5880 | 0.8489 | 0.5514 | 107.00 | 207.89 |
| scifact | tuned hybrid | 0.6847 | 0.9487 | 0.6456 | 369.92 | 465.03 |
| scifact | tuned sparse | 0.5880 | 0.8489 | 0.5514 | 110.71 | 216.22 |
| scidocs | default dense | 0.2128 | 0.4313 | 0.3553 | 983.72 | 1187.32 |
| scidocs | default hybrid | 0.1928 | 0.3997 | 0.3326 | 1190.16 | 1817.72 |
| scidocs | default sparse | 0.1389 | 0.2967 | 0.2506 | 263.33 | 706.41 |
| scidocs | tuned hybrid | 0.1866 | 0.3977 | 0.3216 | 1198.68 | 1818.79 |
| scidocs | tuned sparse | 0.1389 | 0.2967 | 0.2506 | 263.64 | 701.95 |

## Decision

The SciFact development split selected hybrid `k1=0.8`, `b=0.4`, `rrf_k=20`. Sparse selection retained `k1=1.2`, `b=0.75`.

Tuned minus unchanged hybrid nDCG@10 on scifact: +0.0177 (paired 95% interval [+0.0059, +0.0297]; 300 queries).
Tuned minus unchanged hybrid nDCG@10 on scidocs: -0.0063 (paired 95% interval [-0.0105, -0.0021]; 1000 queries).

The transfer reverses direction across the two tasks. Reject the SciFact-tuned hybrid configuration as a global default. Keep product defaults unchanged; consider a scope-specific change only after representative application-corpus evaluation and owner review.

## Protocol

These are paper-level rankings collapsed from the production top-100 chunk pool, so fewer than 100 papers can be returned. Latency covers warm local retrieval and query embedding, excluding HTTP, authentication and database work. SCIDOCS uses SciFact-selected parameters because it has no training split; no model was trained. The benchmark's opt-in lossless wordpiece refinement differs from the product's default PDF upload chunking and is recorded in snapshot provenance. This does not evaluate PDF extraction, answers, private-scope isolation, or concurrency.

The grid was committed before held-out evaluation. Development selection uses only the deterministic SciFact training subset. Dense has no tuned parameters. Sparse and hybrid select their configurations independently by development nDCG@10. The JSON retains query IDs, per-query rankings, failures, corpus and input hashes, model/tokenizer revision and hashes, source hashes, and paired confidence intervals.
SciFact development and test questions search the same SciFact corpus. Query-ID overlap is rejected, but paraphrase-level leakage and near-duplicate paper versions were not audited; these results do not establish broader-domain generalization.

## Build measurements

| Dataset | Papers | Chunks | Import ms | Embedding ms | Sparse segment build ms | Warm embedding cache |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| scifact | 5183 | 41983 | 58306.42 | 958850.12 | 9593.53 | True |
| scidocs | 25657 | 176739 | 482549.50 | 6040674.39 | 74390.22 | True |

Embedding build times may include reuse from verified per-text caches; they are not cold-build claims. Sparse queries use the shipped in-memory reference kernel via an offline pipe, whose startup measurement is recorded separately from immutable sparse segment construction. Peak memory was not sampled. Methods run in fixed order, which can affect timing through cache and thermal effects.

## Paired bootstrap

Intervals are descriptive query-paired percentile intervals for right minus left; they are not corrected for multiple comparisons. Recall uses its declared 100 cutoff; nDCG and MRR use 10.

| Dataset | Comparison | Metric | Mean delta | 95% interval | Paired queries |
| --- | --- | --- | ---: | --- | ---: |
| scifact | default_hybrid_vs_tuned_hybrid | ndcg | 0.0177 | [0.0059, 0.0297] | 300 |
| scifact | default_hybrid_vs_tuned_hybrid | mrr | 0.0157 | [0.0025, 0.0293] | 300 |
| scifact | default_hybrid_vs_tuned_hybrid | recall | 0.0000 | [0.0000, 0.0000] | 300 |
| scifact | default_sparse_vs_default_dense | ndcg | 0.0855 | [0.0440, 0.1265] | 300 |
| scifact | default_sparse_vs_default_dense | mrr | 0.0823 | [0.0376, 0.1263] | 300 |
| scifact | default_sparse_vs_default_dense | recall | 0.0794 | [0.0379, 0.1217] | 300 |
| scifact | default_sparse_vs_default_hybrid | ndcg | 0.0789 | [0.0528, 0.1063] | 300 |
| scifact | default_sparse_vs_default_hybrid | mrr | 0.0785 | [0.0476, 0.1101] | 300 |
| scifact | default_sparse_vs_default_hybrid | recall | 0.0997 | [0.0675, 0.1339] | 300 |
| scifact | default_sparse_vs_tuned_sparse | ndcg | 0.0000 | [0.0000, 0.0000] | 300 |
| scifact | default_sparse_vs_tuned_sparse | mrr | 0.0000 | [0.0000, 0.0000] | 300 |
| scifact | default_sparse_vs_tuned_sparse | recall | 0.0000 | [0.0000, 0.0000] | 300 |
| scidocs | default_hybrid_vs_tuned_hybrid | ndcg | -0.0063 | [-0.0105, -0.0021] | 1000 |
| scidocs | default_hybrid_vs_tuned_hybrid | mrr | -0.0110 | [-0.0208, -0.0015] | 1000 |
| scidocs | default_hybrid_vs_tuned_hybrid | recall | -0.0021 | [-0.0054, 0.0011] | 1000 |
| scidocs | default_sparse_vs_default_dense | ndcg | 0.0739 | [0.0640, 0.0841] | 1000 |
| scidocs | default_sparse_vs_default_dense | mrr | 0.1046 | [0.0851, 0.1249] | 1000 |
| scidocs | default_sparse_vs_default_dense | recall | 0.1346 | [0.1213, 0.1483] | 1000 |
| scidocs | default_sparse_vs_default_hybrid | ndcg | 0.0539 | [0.0473, 0.0608] | 1000 |
| scidocs | default_sparse_vs_default_hybrid | mrr | 0.0820 | [0.0680, 0.0964] | 1000 |
| scidocs | default_sparse_vs_default_hybrid | recall | 0.1031 | [0.0921, 0.1138] | 1000 |
| scidocs | default_sparse_vs_tuned_sparse | ndcg | 0.0000 | [0.0000, 0.0000] | 1000 |
| scidocs | default_sparse_vs_tuned_sparse | mrr | 0.0000 | [0.0000, 0.0000] | 1000 |
| scidocs | default_sparse_vs_tuned_sparse | recall | 0.0000 | [0.0000, 0.0000] | 1000 |

## Environment

```json
{
  "cpu": "Intel64 Family 6 Model 170 Stepping 4, GenuineIntel",
  "engine_sha256": "61004e31ae02fa21852dbadd0d877d1769ce1d0a828192b805ae17f9a8cbe74c",
  "engine_version": "retrievald 0.1.0",
  "git_commit": "eee9086c1f9c7568caae6267094c6c3b932a1712",
  "logical_cpus": 22,
  "memory_note": "Not sampled; do not infer memory efficiency",
  "peak_memory": null,
  "platform": "Windows-11-10.0.26200-SP0",
  "python": "3.13.15",
  "thread_environment": {
    "OMP_NUM_THREADS": "2",
    "OPENBLAS_NUM_THREADS": "1"
  },
  "tracked_diff_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

## Reproduce

Complete the [native setup](docs/DEVELOPMENT.md#native-setup) first. Replace `python` with `.\.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on Linux.

```sh
python scripts/benchmark_beir.py --phase preflight
python scripts/benchmark_beir.py --phase prepare
python scripts/benchmark_beir.py --phase tune
python scripts/benchmark_beir.py --phase evaluate --output docs/results/benchmark-2026-10-01.json
python scripts/render_beir_report.py docs/results/benchmark-2026-10-01.json
```

The checksum-verified archives and generated artifacts stay under ignored `artifacts/`. Use a new work directory if protocol, model or subset configuration changes. Windows users can pre-download the official archives with `Invoke-WebRequest` into `artifacts/beir/downloads/` if Python cannot validate the host certificate chain; do not disable TLS verification. The runner still verifies the published checksums.

```powershell
New-Item -ItemType Directory -Force artifacts/beir/downloads | Out-Null
Invoke-WebRequest -Uri 'https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip' -OutFile artifacts/beir/downloads/scifact.zip
Invoke-WebRequest -Uri 'https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scidocs.zip' -OutFile artifacts/beir/downloads/scidocs.zip
```

CI runs a deliberately small real-model subset as a pipeline regression only. It is never evidence of MiniLM quality or full-corpus speed.
