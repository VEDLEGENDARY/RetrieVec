# Implementation status

## Weeks 1–4 continuation

Weeks 3–4 step 6: artifact-store identity resolution and register/prepare/ready/CAS
publication implemented. Registration is idempotent; lost activation responses
reconcile against the active ID. PostgreSQL ownership/readiness/CAS tests included.

Weeks 3–4 step 5: PostgreSQL 18 migration, ownership checks, immutable registry,
ready-state resolution and active-parent CAS implemented; local Compose provided.

Weeks 3–4 step 4: shared reader abstraction, immutable multi-segment manifests,
aggregate statistics, content identities and memory/disk search parity tests added.
The build CLI publishes artifacts; database activation remains a separate operation.

Weeks 3–4 step 3: bounded canonical decoder, checksummed admission, per-term disk
reads, immutable publication, corruption/fuzz fixtures implemented. No eager index
rebuild is used by the segment reader; validation discards decoded postings.

Weeks 3–4 step 2: deterministic compressed segment encoder and independently
constructed one-token golden bytes implemented. Reader validation follows next.

Weeks 3–4 step 1: authoritative segment contract and snapshot/registry/RPC ADR
added. Prior implementation gates are audited; reviewed relevance remains open.

Weeks 1–2 step 14: one-command sparse demonstration, repeated capture, draft metric
replay and latency artifacts implemented. Clean-start execution is scheduled for
the final validation batch. Reviewed quality acceptance remains explicitly open.

Weeks 1–2 step 13: bounded parser fuzz seeds, repeatable 1,000-document Go search
benchmark, and serial/concurrent HTTP latency capture implemented. Performance
numbers will be recorded only from actual runs; no timing thresholds gate CI.

Weeks 1–2 step 12: saved-run metric replay, per-query/aggregate reports and explicit
undefined/unjudged conventions implemented. Independent numeric tests included;
validation and baseline capture follow the implementation batch.

The owner authorized completing both plans, batching implementation before final
validation, and the existing feature-branch/PR workflow. A pre-existing README
naming edit is preserved outside these implementation commits.
Weeks 1–2 step 11: versioned synthetic draft pool, frozen splits and review
provenance validation implemented. Human review and real-corpus expansion remain
evidence gates; no generated labels are described as reviewed.

Recovery and steps 1–10 are implemented. The owner authorized restoration after
PR #4, checks at the end, and PR integration. Existing shared history is preserved.
Ten new milestone commits restore steps 1–5 and add steps 6–10. The naming migration
is included in the workspace restoration.

| Step | Capability | Commit / branch |
| --- | --- | --- |
| 1 | Workspace, CI, Retrieval Lab naming | e84f4d8 / chore/restore-workspace |
| 2 | Deterministic corpus snapshots | a3c0917 / feat/restore-corpus-snapshots |
| 3 | Versioned Go analyzer | 36f653a / feat/restore-versioned-analyzer |
| 4 | Text/PDF import and paragraph chunking | d2a1a31 / feat/restore-paper-import |
| 5 | Validated loader and immutable positional index | f07f71e / feat/restore-positional-index |
| 6 | BM25 ranking and explanations | 1e00be6 / feat/bm25-ranking |
| 7 | Bounded structured query parser | 7165bfa / feat/structured-query-parser |
| 8 | Boolean and positional phrase execution | 812dd8b / feat/boolean-phrase-search |
| 9 | Local HTTP service and graceful shutdown | fe37767 / feat/sparse-http-api |
| 10 | Python client and reproducible run capture | feat/python-run-capture; SHA recorded in PR |

## Validation on 2026-09-14

The shared check script passed on Windows with Go 1.26.8 and Python 3.13.15:
Go formatting, vet, all eight package test suites, executable build, Python
dependency consistency, Ruff lint/format and all 21 Python tests.
Live integration starts the actual Go service, searches the synthetic corpus,
captures syntax errors, and verifies repeated ranking hashes. Go tests cover
independent BM25 scores, deterministic ties, parsing limits, reference Boolean
predicates, repeated phrases, scoped negation, zero-score matches, HTTP limits,
and concurrent index/API reads.

Hosted Windows/Linux CI and Linux race checks are pending publication; their
actual conclusions will be recorded in PRs before integration. No independent
review is claimed. Main is updated only through PRs.

Step 4's five-paper audit produced 193 chunks over 68 pages, with exact extracted
page reconstruction and a maximum of 256 tokens per chunk. Source pins and
visual inspection limitations are in [the seed report](reports/seed-import-v1.md).
Downloaded papers and generated artifacts remain ignored.

## Remaining scope

Steps 11–14 (owner-reviewed judgments, retrieval metrics, performance/fuzz
harnesses, final demonstration/handoff) remain incomplete and outside this batch.
No retrieval-quality or latency benchmark claims are made. Index persistence,
dense retrieval, authentication, OCR and synthesis are later milestones.
