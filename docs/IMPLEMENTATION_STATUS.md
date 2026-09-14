# Implementation status

## Recovery batch, 2026-09-14

Step 6: BM25, free-text OR candidates, stable ties and term explanations implemented.
Independent score fixtures included; validation scheduled at batch end.

The owner authorized restoration after PR #4, steps 6–10, checks at the end,
and PR merges. Shared history is preserved. Ten recovery milestone commits
restore steps 1–5 and add steps 6–10; naming is included in step 1.
Recovered steps: 1 e84f4d8, 2 a3c0917, 3 36f653a, 4 d2a1a31.
Step 5 restores the loader/index and adds corruption coverage. Batch checks pending.
The entries below describe the original implementation history.

The weeks 1–2 plan contains 14 sequential commit-sized steps. Steps 1–4 are
implemented locally; hosted CI remains pending. Steps 2–5 are an owner-authorized
batch of separate commits on stacked feature branches. Main changes only through PRs.

## Step 1: workspace scaffold

State: committed; local checks pass; hosted CI pending.
Commit ID: `e0a5e7e`.
Proposed branch: `chore/workspace-scaffold`.
Proposed commit: `chore: scaffold Go and Python workspace with CI`.

Delivered:

- Go module, service CLI scaffold, and seven documented internal package boundaries.
- Installable Python package with corpus/client/evaluation boundaries and CLI.
- Exact development/build tool pins, ignore rules, and LF line-ending policy.
- Windows/Linux setup commands and a shared cross-platform check script.
- CI matrix with pinned actions, read-only permissions, and Linux race checks.
- Architecture overview, initial ADR, contribution workflow, and dataset/doc locations.

Validation on 2026-09-13:

| Check | Evidence |
| --- | --- |
| Environment | Windows 10.0.26200, amd64; Go 1.26.8; Python 3.13.15 |
| Python setup | Fresh isolated environment; pinned tools and editable package installed |
| Shared check command | `python scripts/check.py` exited 0 |
| Go formatting and static analysis | `gofmt -l` returned no files; `go vet ./...` passed |
| Go tests | CLI table passed all six cases via `go test -count=1 ./...` |
| Go executable | Built successfully; `retrievald --version` returned `retrievald 0.1.0` |
| Python dependency consistency | `pip check` found no broken requirements |
| Python lint and formatting | Ruff checks passed; eight files formatted |
| Python tests | Four unittest tests passed, including installed console/module entry points from a temporary directory |
| Hosted CI and Linux race checks | Configured, not run; await approved branch/PR |

Checks ran in an isolated staging workspace to preserve main while branch and
commit approval is pending. The entry points do not yet process a corpus or serve
HTTP. Empty internal packages intentionally contain only package documentation.

## Remaining sequence

| Step | Capability | State |
| --- | --- | --- |
| 2 | Validated deterministic corpus snapshots | Implemented; local checks pass |
| 3 | Versioned analyzer and token fixtures | Implemented; local checks pass |
| 4 | Local paper import and paragraph chunking | Implemented; synthetic tests and real seed audit pass |
| 5 | Positional inverted index | Not started |
| 6 | BM25 free-text ranking | Not started |
| 7 | Structured query parser | Not started |
| 8 | Boolean and phrase execution | Not started |
| 9 | Local HTTP service | Not started |
| 10 | Python client and run capture | Not started |
| 11 | Owner-reviewed evaluation dataset | Not started; actual owner review required |
| 12 | Metrics and baseline reports | Not started |
| 13 | Fuzz, concurrency, and performance harnesses | Not started |
| 14 | Reproducible demo and milestone handoff | Not started |

## Open gates and next action

Step 1 is recorded as e0a5e7e and naming migration as fcaf4be. Complete the authorized
steps 2–5 in order, then present the local branch stack for PR approval. No hosted CI
or independent review has been performed for the implementation branches.

No retrieval benchmarks, quality metrics, reviewed labels, persistent segments,
or RPC implementation are claimed.

## Step 2: deterministic corpus snapshots

Branch: feat/corpus-snapshots. Commit ID: c3d62b1.
Strict record fields, content IDs, manifest provenance, canonical hashes, UTF-8
validation, staged publication, and twelve synthetic fixtures are implemented.
The shared check script passed with 13 Python tests, Go tests/vet/build, and Ruff.
Snapshot size is bounded to 64 MiB per file. Publication is validated but does not
claim crash durability. CLI: retrievallab validate-snapshot <snapshot-directory>.

## Step 3: versioned analyzer

Branch: feat/versioned-analyzer. Commit ID: ed936a7.
Go implements letter/decimal-digit runs, simple Unicode lowercase, zero-based
positions, and original UTF-8 byte offsets. Python uses the same executable.
Fifteen shared Unicode fixtures and malformed/oversized-input checks pass, along
with all shared checks (15 Python tests and Go tests/vet/build). No stemming or
normalization is applied. Behavior and the Unicode table version identify the analyzer.

## Step 4: local import and chunking

Branch: feat/paper-import. Commit ID: a899953.
Pinned PDF extraction and UTF-8 imports validate source hashes and publish only
complete snapshots. Paragraph packing uses Go token counts and original offsets.
The shared checks pass with 19 Python tests and Go tests/vet/build. Five real
papers produce 193 chunks across 68 pages; repeated runs produce the same ID.
Every page reconstructs exactly, with no omitted pages and no chunk over 256 tokens.
See docs/reports/seed-import-v1.md for source pins, inspection, and limitations.

## Step 5: positional inverted index

State: committed; local focused tests are present but Go validation was unavailable in this shell.
Branch: feat/positional-index.
Commit ID: 9670222.
Commit: `feat: build positional inverted index`.

The immutable Go index assigns internal IDs by external chunk ID, stores sorted
term postings with zero-based positions, preserves chunk metadata, computes
collection statistics, and returns defensive copies for concurrent readers.
Focused tests cover posting invariants, deterministic ordering, rejected input,
defensive copies, and concurrent read access. Persistent index files and ranking
are deferred to later milestones.
