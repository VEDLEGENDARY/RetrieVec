# RetrieVec: ML and Index Experiments Handoff (Weeks 11–12)

## Required engineering workflow

Read and follow [ENGINEERING_WORKFLOW.md](ENGINEERING_WORKFLOW.md) in full before changing the repository. Its approval boundaries are part of this handoff.

- Work on only the first incomplete commit-sized step.
- Obtain approval for the proposed branch before creating or switching to it.
- Never implement or commit directly on `main`/`master`; integrate only through an approved pull request.
- After implementation and validation, present the diff, checks, limitations, and exact message; obtain approval before committing.
- Obtain separate authorization before pushing, opening/updating a pull request, merging, or starting the next step unless that exact action is already authorized.
- Use natural, project-focused branch names, commit messages, code, comments, documentation, and PR descriptions. Do not add tool attribution or fabricated authorship/review.
- Preserve unrelated changes and record actual evidence and incomplete gates honestly.
## Objective

Strengthen the system through controlled reranker training, approximate-retrieval experiments, and measured index optimization. This is an advanced milestone after a reproducible working release; dates may extend. Read all earlier plans and actual implementation status.

Success is a sound experiment and a defensible retain/reject decision, not an assumed improvement. Keep exact dense search and the correct sparse implementation as references. Do not force an experimental model/index into the default product.

## Experiment integrity

Version corpus, judgments, splits, model/code/configuration, random seeds, dependencies, and run outputs. Separate train/development/held-out data, controlling for paper versions and near-duplicate passages. Keep labels and benchmark history auditable.

Reviewed relevance judgments are the quality reference. Synthetic/pseudo-labeled training examples must carry provenance and must not be reported as human-reviewed evaluation. Avoid training on held-out questions, their paraphrases, or held-out paper evidence when measuring paper-level generalization.

## Reranker study

Establish the unmodified pretrained reranker baseline first. Select a modest supported model using current official documentation/license and available accelerator resources. Pin revision, tokenizer, maximum input length, scoring semantics, and query/passage formatting.

Mine hard negatives from training-only sparse/dense/hybrid candidate pools. Unjudged is not synonymous with irrelevant: review uncertain negatives or exclude them. Document positive/negative balance, sampling, truncation, loss, batch size, optimizer, learning rate, epochs, seed, and checkpoint selection.

Run bounded training with resumable checkpoints and a recorded resource/spending budget. Select checkpoints on development data only. Compare no reranker, unchanged reranker, and fine-tuned reranker on the same candidate pools and held-out queries. Report ranking quality, support impact, latency, memory, and failures. Candidate recall is an upper bound on what reranking can recover.

## Approximate vector study

Compare one established approximate backend against exhaustive cosine search using identical vectors, scope, snapshot, and query set. Measure ANN neighbor recall@k separately from judged relevance metrics. Record build time, memory/disk, p50/p95 latency, parameters, and corpus scale.

Only implement a custom ANN extension if there is a defined algorithmic learning question and enough time for reference tests. A VP-tree is not mandatory; high-dimensional embeddings may provide weak pruning. A negative result with distance-count measurements is valid evidence. Do not substitute low-dimensional toy results for embedding-corpus claims.

## Sparse index optimization

Implement compaction only with immutable output, external-ID preservation, aggregate-statistics equivalence, and atomic snapshot publication. Keep old segments while referenced. Reader/writer lifecycle tests must cover concurrent queries and interrupted compaction.

Select one additional measured optimization, such as bounded top-k selection or posting skip metadata. Changing disk layout requires a new documented version, golden fixtures, and an explicit migration/compatibility policy. Do not reinterpret `RLSEG001` bytes under a different layout.

## Product integration

Expose experimental configurations in saved runs with explicit model/index versions. Defaults change only after reviewed quality/resource tradeoffs support the choice and the owner approves the change. Keep rollback to the stable configuration. Re-run private-scope and pinned-snapshot checks for every backend/model adapter.

## Fourteen commit-sized steps

| Step | Commit message | Deliverable and validation |
|---|---|---|
| 1 | `docs: define training and retrieval experiment protocols` | Hypotheses, frozen splits, resource bounds, retain/reject criteria |
| 2 | `feat: build provenance-aware training datasets` | Versioned samples and paper/near-duplicate leakage checks |
| 3 | `feat: evaluate pretrained reranker baseline` | Real model identity, candidate pool and quality/latency report |
| 4 | `feat: mine reviewed training hard negatives` | Training-only mining, uncertainty filtering, sampling report |
| 5 | `feat: add resumable reranker training pipeline` | Bounded training, checkpoints, seed/config logging |
| 6 | `test: compare reranker checkpoints on held-out queries` | Frozen selection, three-way comparison, failures and uncertainty |
| 7 | `feat: register optional versioned reranker configurations` | Stable fallback, result provenance, private-scope integration |
| 8 | `feat: add approximate dense retrieval adapter` | Same-vector exact reference, snapshot/scoping parity |
| 9 | `test: benchmark approximate retrieval tradeoffs` | Neighbor recall vs relevance, latency/resource curves |
| 10 | `feat: compact immutable sparse index segments` | Rank/statistics equivalence and external-ID preservation |
| 11 | `test: verify interrupted compaction and pinned readers` | Atomic publication, retained snapshots, no partial visibility |
| 12 | `perf: optimize measured sparse retrieval bottleneck` | One justified optimization or documented rejected experiment |
| 13 | `test: compare final model and index configurations` | End-to-end quality/resource/isolation regression report |
| 14 | `docs: publish experiment findings and portfolio evidence` | Reproduction commands, limitations, measured résumé drafts, next decisions |

Custom ANN is optional after these steps, with its own approved plan. Do not displace required evaluation to implement it. If training data/resources are insufficient, retain the unchanged model and document the blocker; infrastructure tests alone do not count as completed fine-tuning.

## Acceptance

All reported experiments have reproducible configuration and actual results; data leakage checks pass; model/index choices state tradeoffs; experimental paths preserve privacy and snapshots; stable defaults remain recoverable. Document negative results as well as improvements in `docs/reports/ml-index-experiments.md`. Record incomplete gates in implementation status.

This completes the planned initial release plus advanced extraction and ML/index tracks. Public release, deployment, scheduled monitoring, collaboration, and arbitrary paper-code execution require separate scope decisions.

## Implementation task prompt

> Read this handoff completely, then read Plans/ENGINEERING_WORKFLOW.md, prerequisite plans, repository instructions, and implementation status. Follow every approval boundary. Work only on the first incomplete commit-sized step: propose its branch, scope, checks, and commit message, then wait for branch approval before changing code. After approval, implement and validate only that step, present the complete diff and results, and wait for commit approval. Do not work directly on main, push, open or merge a pull request, or begin another step without the required authorization. Keep repository language natural and project-focused, preserve unrelated work, and report actual evidence and incomplete gates.
