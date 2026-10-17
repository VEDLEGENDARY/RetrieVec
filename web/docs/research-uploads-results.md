# Research, uploads, and retrieval results

Task 03 builds on the merged search workbench. Changes stay in `web/` except the approved extraction provenance extension in the upload API and ingestion worker.

## Research conversations

The conversation rail shows titles, dates, and a one-line question preview. Recent collection run summaries provide previews without downloading every saved answer. Conversations outside that summary window explicitly offer to load their latest question; opening one hydrates its preview from authorized history. The date is labelled as the latest saved run or conversation creation date. Navigation waits for an in-flight submission to finish.

Answers retain their saved text, model configuration, snapshot, and evidence. Paragraphs use Newsreader at the reading size with citations in a margin column; mobile puts citations below each paragraph. Numbered citation buttons open passage, source title, and snapshot previews on hover or focus. Enter opens the existing source inspector. Escape dismisses previews and the inspector restores focus. Unresolved references remain visible warning chips.

The four-stage status strip follows the existing live run state. Failed or cancelled runs do not infer completed stages from an error code. Failures offer a pinned-question retry and copying diagnostic details. The existing event stream, early retrieved evidence, validated-answer publication, live authorization checks, and authenticated cancellation endpoint remain in use.

## Upload review and provenance

The review queue accepts drag and drop or the native file chooser. Rows show filename, size, media type, local validation, and removal. Unsupported, empty, or oversized files block submission. Server validation still checks actual file content. An unchanged batch retains its request key across an unconfirmed response and retry; changing the batch creates a new key. Refreshing upload status does not change it.

Processing rows identify each original file and explicitly label the worker's shared batch stage. No per-file percentage is invented. After success, rows show retained extractor names and revisions, OCR usage, extraction version, and the original source hash. Older jobs and unknown extraction versions say when metadata was not retained or reported.

The worker derives provenance from the actual corpus extraction version and, for typed evidence, the validated evidence bundle. It retains only profiles for the current job's uploaded sources in the existing fenced activation transaction. Authorized job views join the original file records in one query and expose the corresponding profile. No database migration or new endpoint is required. Existing ownership, collection access, and CSRF checks remain in force.

The acceptance test measures focus-to-paint with 500 retained file rows. The review queue itself is bounded to ten files. Virtualization is unnecessary at the measured size; the test guards interaction latency before adding complexity.

## Pinned benchmark results

`/results` renders ten pipeline measurements from the October 1 report. The repository stores `docs/results/benchmark-2026-10-01.json.gz`; `scripts/sync-results.mjs` reads that logical JSON and generates the typed subset in `src/features/results/data.ts`. The full recursive structure fingerprint and semantic checks reject schema drift, incomplete queries, invalid metrics, and changed cutoffs. `npm run build` checks that generated values are current.

The existing container frontend stage copies only `web/`. A byte-identical compressed mirror in `web/benchmarks/` permits the same validation in isolated frontend builds. It is a build input and is not included in `dist/`. No second benchmark report is read. Runtime data excludes per-query records and environment paths.

The table supports keyboard sorting, scoped row and column headers, a caption, sticky headers, and tabular metrics. A hand-built SVG labels every dataset/pipeline point directly and provides equivalent textual values. Limitations beside the table explain chunk-pool paper ranking, excluded HTTP and database latency, transferred SciFact parameters, pretrained embeddings, and the absence of answer or PDF extraction evaluation. The later October 5 README measurements are explicitly distinguished from this page's October 1 data.

The production build includes a static `results/index.html` entry so the installed frontend serves the route directly. All fonts and data remain local.

## Verification

Run `npm run build`, `npm run test:ui`, and `npm test` from `web/`. The integration test requires the isolated PostgreSQL DSN, installed Python package, and built retrieval engine described by the existing test server. Run Python regressions and `python -m retrievec.contracts --check` for the provenance extension.

Browser coverage includes citation keyboard previews, unresolved warnings, saved conversation reopening, live stages, authenticated cancellation, upload review/removal, request-key recovery, retained provenance, results sorting, and axe scans in both themes at desktop and mobile widths. The real-service test checks upload through worker activation, provenance, direct Results routing, evidence access, cancellation, and second-user isolation.

`scripts/check-bundle.mjs` sums gzip sizes of every built JavaScript and CSS asset against the merged Task 02 baseline of 114,664 bytes. The build fails if Task 03 growth reaches 25,000 bytes. No runtime dependency is added.
