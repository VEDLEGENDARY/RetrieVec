# Implementation status

The weeks 1–2 plan contains 14 sequential commit-sized steps. Steps 1–3 are
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
| 4 | Local paper import and paragraph chunking | Not started |
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

Branch: feat/versioned-analyzer. Commit ID recorded in the next status update.
Go implements letter/decimal-digit runs, simple Unicode lowercase, zero-based
positions, and original UTF-8 byte offsets. Python uses the same executable.
Fifteen shared Unicode fixtures and malformed/oversized-input checks pass, along
with all shared checks (15 Python tests and Go tests/vet/build). No stemming or
normalization is applied. Behavior and the Unicode table version identify the analyzer.
