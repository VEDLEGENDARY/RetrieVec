# BEIR retrieval benchmark

Measured source: [docs/results/benchmark-2026-10-01.json](docs/results/benchmark-2026-10-01.json).

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

These are paper-level rankings collapsed from the production top-100 chunk pool, so fewer than 100 papers can be returned. Latency covers warm local retrieval and query embedding, excluding HTTP, authentication and database work. SCIDOCS uses SciFact-selected parameters because it has no training split; no model was trained. The opt-in lossless wordpiece refinement is recorded in snapshot provenance. This does not evaluate PDF extraction, answers, private-scope isolation, or concurrency.

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

Complete the README native setup first. Replace `python` with `.\.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on Linux.

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
