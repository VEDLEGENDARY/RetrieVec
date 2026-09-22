# ML and index experiment findings

Status: experiment infrastructure implemented; experiments not run.

The [versioned protocol](../ml-index-protocol.md) defines the hypotheses,
split/leakage boundaries, resources and retain/reject procedure for Weeks 11–12.
It is a protocol specification, not an executed or frozen study manifest.

| Study | Current result | Decision |
|---|---|---|
| Reviewed training data | Provenance schema and leakage checks implemented; reviewed samples and frozen splits unavailable | Pending |
| Pretrained reranker | Pinned adapter/evaluation contract implemented; model selection and hardware smoke pending | Retain current configuration |
| Fine-tuned reranker | Bounded resumable pairwise trainer and selection contract implemented; training not run | Retain current configuration |
| ANN | Snapshot-scoped deterministic IVF experiment and benchmark harness implemented; comparison not run | Retain exact cosine |
| Sparse compaction | RLSEG001 immutable merge and lifecycle fixtures implemented; execution not run | Retain existing immutable segments |
| Sparse optimization | Bounded top-k parity prototype still consumes the sorted reference; no measured improvement | Reject prototype; retain correct scorer |
| Product promotion | No reviewed tradeoff evidence | No default change |

No test, benchmark, model download or training run was executed in this coding
batch, as requested. No numeric results are claimed. Reviewed data, current
model/license selection, hardware availability and execution are still required
to produce a retain decision.

Implemented components:

- `retrievec.experiments.training_data`: content identities, provenance and
  fail-closed paper/query/passage-cluster leakage checks.
- `reranker`, `negatives`, `training`, `comparison`: unchanged baseline,
  reviewed training-only mining, atomic checkpoints and dev-only selection.
- `config_registry`: content-addressed opt-in configs with exact/BM25 fallback.
- `ann` and `ann_benchmark`: snapshot parity, exact reference, ANN recall and
  relevance/resource separation.
- Go segment compaction: external-ID/statistic preservation, source retention,
  content-addressed validation and atomic publication under RLSEG001.
- `decision` and `scripts/compare_ml_indexes.py`: conservative final decision;
  missing reviewed evidence produces `inconclusive` and never changes defaults.

After approved data and criteria exist, the final decision command is:

```text
python scripts/compare_ml_indexes.py \
  --reference artifacts/experiments/reference.json \
  --experimental artifacts/experiments/experimental.json \
  --criteria artifacts/experiments/criteria.json \
  --output artifacts/experiments/decision.json
```

This is an executable interface, not proof that those private artifacts exist.
The IVF implementation is a deterministic experimental reference rather than a
selected production backend. The top-k prototype is rejected because it begins
from the fully sorted scorer and therefore cannot improve the measured bottleneck.

Previous implementation through PR #24 is integrated in main at `11d9404`.
Earlier human answer review and real extraction-quality acceptance remain open.
Infrastructure CI success does not close those gates or establish release readiness.
