# Implementation status

The weeks 1–2 plan contains 14 sequential commit-sized steps. Only step 1 has
been implemented for review. No later capability is implemented by this scaffold.

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
| 2 | Validated deterministic corpus snapshots | Not started |
| 3 | Versioned analyzer and token fixtures | Not started |
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

Obtain approval for the step 1 branch and commit, link the work to an issue, apply
the reviewed scaffold to the approved branch, and open a focused PR. Record the
real commit ID in the next status update and CI evidence after an actual run.
Main changes only through a reviewed PR; repository protection settings remain
unverified. Begin step 2 after the owner-approved step 1 workflow is complete.

No retrieval benchmarks, quality metrics, reviewed labels, persistent segments,
or RPC implementation are claimed.
