# Performance baseline and measurement contract


## Current verification — 2026-10-05

The 1,300-query retrieval study and phase 4 CPU answer run are recorded in
[BENCHMARKS](../../BENCHMARKS.md) and [ANSWER_EVAL](../../ANSWER_EVAL.md).
Worker TTFT is implemented and measured for 11 completed Qwen cases. Provider
tokens stream provisionally before validated publication; the historical
non-streaming baseline below describes the earlier implementation. Representative
PDF ingest and concurrent-user service measurements remain unverified.

## Phase 3 hybrid diagnostic profile

The sequential offline hybrid path was profiled on 10 queries from the frozen SciFact
development split, using the complete legacy corpus and cached pinned MiniLM model.
[Per-query observations](../results/hybrid-profile-development-2026-10-04.json)
retain sparse, dense, fusion and wall-clock durations. Under cProfile, the run took
2.311 seconds: exact dense search accounted for 1.568 seconds cumulatively, sparse
retrieval for 0.604 seconds, and query-encoder ONNX execution for 0.128 seconds.
These are instrumented diagnostic observations, not held-out latency percentiles.
Dense scoring includes validation of vector IDs, finiteness and normalization;
this phase preserves those checks. The profile motivates overlapping the two legs,
with exact ranking/score parity and separate alternating-order wall-clock measurements
required before changing the scheduling default. The completed 1,300-query study
verified exact parity and lower paired latency on both tasks; bounded concurrent
scheduling is now enabled. See BENCHMARKS.md for measurements and session limitations.

2026-09-29. Plan 3, measurement increment only. Source base: `f6e021142df2f4a4990b7b4c2b28da45bd485882` plus the uncommitted browser recorder/test. Plans 1 and 2 remain at their review gates. No motion, navigation, cache, persistence, or streaming behavior has changed.

## Historical UI baseline — 2026-09-29

Single local user, Windows, Node 26.1.0, Vite 8.3.0 development server, headless Chromium 153.0.8010.12, 1280×720, no CPU/network throttling. Synthetic HTTP responses supply one collection and an empty hybrid search result. No real corpus, database, embedding model, PDF processing, or generation provider participates. This is a UI baseline, not release throughput or model-quality evidence.

Twelve sequential navigations alternate diagnostics off/on. Discard the first pair; retain five samples per condition. Percentiles use nearest rank; p95 with five samples is the maximum and is not statistically robust. Browser Event Timing samples are individual events, may share an interaction, and exclude events below the browser threshold. They are not independent user actions or an INP score.

| Measurement | Samples | p50 ms | p95 ms | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Workspace heading observed, recorder off | 5 | 436.4 | 490.0 | Navigation time origin to Playwright observing visible heading; includes automation scheduling |
| Workspace heading observed, recorder on | 5 | 414.8 | 473.7 | Same external observation boundary |
| App ready, recorder on | 5 | 375.5 | 442.4 | Navigation time origin to React effect after initial workspace loading settles |
| Retrieval response, recorder on | 5 | 11.6 | 21.8 | Mock request through JSON parsing; **not engine retrieval latency** |
| Reported UI event durations | 85 | 48 | 56 | Browser input delay + handling + next presentation, threshold 16 ms, rounded by browser |
| Real PDF ingest | — | Not measured | Not measured | Existing backend instrumentation; representative ingest run still required |
| Real retrieval / model latency | — | Not measured | Not measured | Requires pinned corpus, service and model configuration |
| Query time-to-first-token | — | Unsupported | Unsupported | Current answer publication is non-streaming; do not substitute response headers or run status |

Observed enabled/off differences are within an uncontrolled small-sample run; **no speed improvement or definitive overhead bound is claimed**. Both conditions include the same built code, so this comparison measures the recorder's enabled behavior, not the entire bundle cost of adding instrumentation. Production build output: JS 277.04 kB (86.15 kB gzip), CSS 26.28 kB (6.87 kB gzip). No previous bundle-size comparison was measured.

Raw baseline saved locally at `artifacts/ui-baseline-2026-09-29.json`. The reproducible test also writes `web/test-results/performance-local-performance-baseline-and-recorder-privacy/ui-baseline.json` and attaches it to its report. These generated paths remain ignored; this document retains the measured summary.

## Instrumentation and definitions

Open the app with `?performance=1`. In browser developer tools:

```js
window.retrievecPerformance.snapshot()
window.retrievecPerformance.clear()
window.retrievecPerformance.eventTimingSupported
```

The recorder is disabled by default. At most 200 samples are retained in memory; snapshots return copies. No queries, paper text, filenames, URLs, resource IDs, session identifiers, or tokens are collected. There is no telemetry upload or persistent storage. Reload clears the buffer. Event Timing support varies; absence of samples does not imply zero latency. This is developer diagnostics, not a new settings interface.

- `app.ready`: initial loading has settled and the corresponding React effect ran. It includes initial navigation/network/module work; it does not assert all hidden views have fetched or that a successful authenticated session exists. It is not LCP or an exact paint timestamp.
- `retrieval.response`: `/api/v1/search` invocation through parsed response or rejection. Fixed outcome `ok`/`error`; aborted requests are in the error bucket. Includes browser/network/API/serialization, not just the ranking algorithm.
- `ui.event`: browser-reported presentation duration, where supported. Threshold and rounding must remain identical for comparisons. Do not average these into a claimed Core Web Vitals INP result.
- PDF ingest already emits `ingestion.claimed.queue_age_ms`, `ingestion.stage.elapsed_ms`, and `ingestion.finished.elapsed_ms` in `registry/jobs.py` and `registry/worker.py`. Whole-attempt duration is separate from queue delay and upload transfer. Filter known PDF workload runs externally; do not infer input type from timing alone. Failed/retried attempts must remain separate from successful completion.
- Request telemetry already emits `http.finished` with operation, status, and elapsed time. Use the search operation for server-side request latency; pair with browser response timing. Existing research run events retain previous-stage elapsed time, and completed results retain total worker elapsed time.
- TTFT requires a real first content-token event and its monotonic origin. Add this when implementing provider streaming. Keep provider-call TTFT separate from user-submit TTFT (which includes queue/retrieval). Do not report an empty/status event as a token, or publish unvalidated content as a final cited answer.

## Reproduce and compare

From `web` with project dependencies and the Playwright browser installed:

```sh
npm run build
npm run test:ui -- performance.spec.ts --workers=1
npm run test:ui -- --workers=1
```


TypeScript/production build passed; all 10 browser checks passed. Benchmark rerun after adding the saved report also passed. Build reports dependency-level Lucide `use client` directive warnings, with no build failure.

Before accepting each later change, repeat its relevant before/after workload on the same browser/hardware/build mode and record commit/diff identity, warm/cold conditions, input hashes, corpus/snapshot, model revision, sample count, p50/p95, failures, and memory where relevant. Use at least 30 measured runs for an initial performance decision; increase if variance masks the proposed effect. This initial five-sample baseline is a smoke measurement, not sufficient for a rollout decision. Keep functional and authorization checks separate from timing comparisons.

Pending representative baseline: chosen concurrency, collection size, PDF pages/bytes and OCR status, model/provider, and hardware. Start with single-user local use until workload is specified. Proposed UI target for review: common interaction presentation p95 below 100 ms; motion never delays dispatch or focus. Real ingestion, retrieval and TTFT budgets must follow measured workloads rather than invented targets.

## Historical Plan 3 requirements and safeguards

1. Representative PDF-ingest/load baselines remain open. Real retrieval and worker TTFT observations are now recorded above; they do not establish production capacity.
2. Stream authorized evidence before generation finishes, then real supported provider tokens. Distinguish provisional output from checked claims; retain cancellation, resumable events and consent rechecks.
3. Optimistically update reversible local actions with rollback. Do not show uploads as searchable, grant consent, or publish an answer before server confirmation.
4. Cache only with defined identity/collection/snapshot/model keys and invalidation on logout, revocation, archive and version change. Inspect existing embedding artifact reuse before adding another cache. Prefetch must be bounded and must not trigger paid generation or relax authorization.
5. Parsing/embedding already run in background workers. Expose their actual stages; do not move them into browser rendering or fabricate progress percentages.
6. Apply approved motion tokens, 150–250 ms entering/exiting, reduced-motion equivalents, immediate input handling. Benchmark layout and panel transitions; remove any motion that impairs responsiveness.
7. Show support and searched scope using actual retrieval provenance. Ranking scores are not confidence probabilities. Insufficient evidence must remain an explicit outcome.
8. Restore drafts, selection and scroll using an identity-scoped, versioned persistence policy with expiry, clearing and quota/error handling. Never restore protected result text without authorization; disclose when browser storage is unavailable. “Never lose” is a design goal, not a guarantee against device/storage loss.
9. Preserve existing PDF drag/drop; add accessible context menus and copy-with-citation, including text alternatives and success/failure feedback. Verify keyboard, touch, focus order and screen-reader behavior.

The owner approved the audit, navigation and implementation. PR #46 contains separate commits for the design system, navigation, evidence inspection, drafts, saved research, streaming and interaction states.

## Follow-up measurements — 2026-09-30

Matched production builds compared baseline `f6e0211` against the implementation through `c8bad4b`. One Chromium instance alternated versions, discarded the first pair, and retained 30 samples per version at 1280×720 on the same machine. HTTP responses were synthetic. Times include browser automation observation overhead; they are not real retrieval-service latency or field INP.

| Observed operation | Baseline p50 / p95 (ms) | Updated p50 / p95 (ms) |
| --- | --- | --- |
| Navigation to workspace heading | 119 / 153.5 | 116.6 / 138.4 |
| Search click to results | 83.2 / 115 | 78.9 / 106.3 |

No regression appeared in this workload. This is not a statistically established speedup or a benchmark of real corpus search. Local raw report: `artifacts/production-baseline-comparison.json`.

The real local Qwen2.5 1.5B Q4_K_M model, llama.cpp b11064, two CPU threads and 4096-token context was also tested with alternating completion/streaming requests against one synthetic evidence passage. Fixed configuration and seed produced the same output SHA-256 across all four requests, and all passed structural validation. Non-streaming totals were 21.844 and 21.369 seconds; streaming totals were 21.025 and 21.482 seconds, with first content at 6.729 and 7.082 seconds. Two samples per mode establish transport parity only, not a resource or quality acceptance decision. Human relevance/support review remains pending.

Reproduce the model comparison with `python scripts/benchmark_generation_stream.py --model <gguf-path> --endpoint http://127.0.0.1:8098 --key-file <key-file> --runs 4 --output <report.json>`. Start the same pinned server/model first. The report records model identity, output hashes and timings without credentials or raw model output. Provider timing starts at invocation; worker first-token timing includes retrieval but excludes queue wait. Local raw report: `artifacts/generation/stream-baseline.json`.

Implemented safeguards include bounded provisional streaming, early authorized evidence, scoped expiring drafts, reduced motion, local removal Undo and owner-only archive restoration. Archive restoration does not resume cancelled work. Remaining gates include full PDF ingest and representative retrieval measurements, polished prose streaming, ordinary-PDF exact highlights, selection/scroll restoration, complete contextual commands, and measured caching/prefetch. These are not claimed complete by the synthetic benchmarks above.
