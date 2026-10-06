# Research provenance extensions

## Section-aware chunking

Implemented as an explicit opt-in: `retrievec import --section-aware`, or
`section_aware: true` in the existing extraction experiment configuration.
The default paragraph packer, token budgets, overlap, and retrieval scoring remain
unchanged. Recognized standalone headings create lossless boundaries; section
context carries across pages. Unknown structure stays unclassified. The original
heading and character offsets in extracted page text are retained in an immutable
hash-bound sidecar referenced by the corpus snapshot. Existing snapshots remain
readable and are never rewritten.

Ask → More section filters exposes the passage-mode filter. Answer mode exposes
it under More answer options. Both filter the bounded **retrieved candidate
pool**, before selecting the final passages. This is not an exhaustive search of
all passages in a section; the UI and result metadata disclose that scope.
Unfiltered requests preserve existing saved-run idempotency hashes.

The complete SciFact/SCIDOCS records were evaluated with the production paragraph
packer at the web's 96-token budget, unchanged BM25 k1=1.2/b=0.75, 100 candidate
chunks, and no wordpiece refinement. There was no tuning. All 300/1,000 test
queries completed for both configurations.

| Corpus | Plain nDCG@10 | Section-aware | Paired delta (95% bootstrap interval) |
|---|---:|---:|---|
| SciFact | 0.619029 | 0.619029 | 0.000000 [0.000000, 0.000000] |
| SCIDOCS | 0.141991 | 0.141484 | −0.000507 [−0.001132, +0.000039] |

SciFact had no recognized headings; SCIDOCS had 593 records with explicit
headings. These are titles and abstracts, not full paper bodies. Dense/hybrid
impact was not measured. The result does not support a default promotion.
Full rankings, metrics and paired intervals:
[sections-2026-10-05.json](../results/sections-2026-10-05.json).

Verification: lossless boundaries, cross-page context, offsets, immutable
provenance and tamper rejection passed unit tests. The section UI test and the
complete 30-test UI suite passed with two browser workers. The web build passed.

## Identifier imports and metadata

`scripts/import_paper.py --arxiv ID --work artifacts/import --output artifacts/store/corpora`
resolves official arXiv metadata and downloads the resolved PDF version. DOI
imports use `--doi DOI --source LOCAL.pdf`: Crossref supplies metadata, while
the explicit local source association is recorded as unverified. Arbitrary
publisher URLs are never followed. Network responses and source sizes are bounded.

Title, authors, publication year and DOI retain field paths, response hashes,
lookup time and source hash in an immutable metadata sidecar. Unknown fields
stay blank. Existing imports do not acquire metadata automatically. Original
files and metadata responses remain in the requested work directory; offline
imports do not create upload records or alter original-source access rules.
Ask passage and answer inspectors show the retained metadata and provenance.

Verification: parser/source-binding tests passed; the four workbench UI tests
and web build passed. A real import of arXiv `2104.08663` resolved version v4,
retained its PDF, title, five authors and publication year 2021, and produced
an immutable sparse corpus. DOI import was checked with deterministic Crossref
fixtures, not a live publisher PDF. Full repository checks passed with both
PostgreSQL and pgvector integrations enabled (142 tests, no skips).
