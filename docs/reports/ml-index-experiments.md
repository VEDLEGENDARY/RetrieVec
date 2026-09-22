# ML and index experiment findings

Status: protocol authored; experiments not run.

The [versioned protocol](../ml-index-protocol.md) defines the hypotheses,
split/leakage boundaries, resources and retain/reject procedure for Weeks 11–12.
It is a protocol specification, not an executed or frozen study manifest.

| Study | Current result | Decision |
|---|---|---|
| Reviewed training data | Reviewed samples and frozen splits unavailable | Pending |
| Pretrained reranker | Model selection and hardware smoke pending | Retain current configuration |
| Fine-tuned reranker | Training, checkpoint selection and held-out comparison not run | Retain current configuration |
| ANN | Backend selection, implementation and comparison pending | Retain exact cosine |
| Sparse compaction | Implementation and lifecycle/equivalence execution pending | Retain existing immutable segments |
| Sparse optimization | No measured bottleneck or improvement recorded | Retain correct scorer |
| Product promotion | No reviewed tradeoff evidence | No default change |

No test, benchmark, model download or training run was executed for this protocol
change, as requested. No numeric results or reproduction commands for unfinished
implementations are claimed. Steps 2–14 remain open; reviewed data, model/license
selection, hardware availability and later execution are required to close them.

Previous implementation through PR #24 is integrated in main at `11d9404`.
Earlier human answer review and real extraction-quality acceptance remain open.
Infrastructure CI success does not close those gates or establish release readiness.
