# Retrieval Lab: Weeks 7–8 Handoff

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

Make the research workspace reliable, measurable, reproducible, and ready for an owner-approved portfolio release. Read all earlier plans and implementation status; inspect actual code before treating prerequisites as complete.

This closes the initial eight-week release. Later plans cover advanced document extraction and ML/index experiments. Dates are planning labels, not deadlines that justify skipping gates. Local operation remains sufficient; deployment and public release require separate approval.

## Scope

Deliver reproducible end-to-end evaluation, failure/load tests, evidence-backed performance improvements, operational documentation, accessible interface polish, and release artifacts. Preserve the Go segment format, snapshot consistency, gRPC contracts, and private collection boundaries.

Avoid introducing new services or replacing established components during hardening. Record baseline → hypothesis → change → correctness checks → measurement for each optimization.

## Reliability contract

- Exercise the whole path: authenticated upload, worker processing, snapshot publication, hybrid query, generation, saved run, and export.
- Test process interruption before/after artifact writes, lease expiry, competing writers, Go restart, model timeout, DB unavailability, stream reconnect, and cancellation.
- Verify recovery does not expose partial snapshots, duplicate effective activations, overwrite newer runs, or leak private evidence.
- Document retry limits, timeouts, concurrency bounds, failure states, and manual recovery commands.
- Test on supported platforms. Process termination is not proof of power-loss durability.
- Keep artifact garbage collection disabled until reference tracking and recovery tests exist. Preserve snapshots referenced by saved runs.

## Observability and load

Correlate request, job, run, and snapshot IDs across Python and Go. Measure queue age, ingestion duration, retrieval stages, generation duration, errors, retries, and active worker counts. Do not log raw private prompts, paper text, tokens, or credentials by default.

Define bounded load profiles: single researcher, concurrent search, simultaneous ingestion/search, and slow model/provider. Report warmup, request count, failures, p50/p95, CPU/RAM, corpus size, and configuration. Separate server timing, network timing, and model time. Include failed/time-out requests rather than reporting only successful latency.

First establish baselines on the owner's hardware. Set regression budgets from measured variability and product needs; do not invent universal latency goals. Offline CI checks correctness, while controlled performance runs produce archived reports.

## Evaluation

Expand toward 40–60 reviewed retrieval questions if owner review time permits, plus a smaller reviewed answer set. Preserve query/judgment provenance and label unjudged candidates explicitly. Create fresh held-out questions if previous sets have been repeatedly inspected.

Report sparse/dense/hybrid quality, judgment coverage, answer support, citation completeness, abstention, and failures separately. Use paired per-query comparisons and uncertainty estimates with sample counts; small samples do not establish broad superiority. Evaluate the exact configuration intended for the demo.

## Security and operational checks

Repeat two-user isolation through direct routes, historical snapshots, cached results, exports, sources, reconnects, and revoked access. Verify CSRF/session controls, upload bounds, safe filenames, model-output rendering, and prompt-injection handling.

Pin dependency versions and inspect selected tools' current official security guidance. Document secrets configuration without committing credentials. Test backup/restore of metadata and referenced immutable artifacts into an isolated environment, including ownership and snapshot references. Never run restore rehearsals over the working dataset.

## Release artifacts

- Tested setup guide, supported hardware/software, and model/download requirements.
- Architecture diagram, selected ADRs, format/RPC contracts, limitations, and recovery guide.
- Versioned benchmark report and reproduction commands.
- Short demo script using redistributable or approved data, showing useful results and an honest limitation.
- Draft résumé bullets whose numbers link to measured runs.
- License/source inventory and repository review for private data and secrets.

Prepare release notes and a candidate release identifier locally. Publishing, tagging/pushing a release, changing repository visibility, and deployment remain separate owner-approved actions.

## Fourteen commit-sized steps

| Step | Commit message | Deliverable and validation |
|---|---|---|
| 1 | `test: audit end-to-end milestone prerequisites` | Actual acceptance inventory and regression fixtures for gaps |
| 2 | `feat: correlate pipeline events and stage metrics` | Safe structured telemetry with cross-service identifiers |
| 3 | `test: add ingestion and activation failure scenarios` | Kill/retry/lease/CAS recovery without inconsistent snapshots |
| 4 | `test: cover generation cancellation and reconnect failures` | Persisted state, late-response protection, retry behavior |
| 5 | `test: expand private workspace isolation coverage` | Two-user source/run/export/cache/revocation checks |
| 6 | `test: add bounded end-to-end load profiles` | Reproducible workloads and complete latency/error accounting |
| 7 | `feat: optimize measured retrieval bottleneck` | Select one justified optimization; reference rank parity and measured result |
| 8 | `feat: bound model and ingestion resource scheduling` | Queue/concurrency/backpressure behavior under mixed load |
| 9 | `test: expand reviewed retrieval and answer evaluation` | Versioned labels, frozen split, owner review, uncertainty/coverage |
| 10 | `fix: improve research workspace usability and accessibility` | Observed usability issues resolved; keyboard/mobile inspection |
| 11 | `test: verify isolated backup and restore` | Metadata/artifact consistency and ownership after restore |
| 12 | `docs: publish reproducible benchmark and recovery guides` | Actual commands/results, limitations, supported environments |
| 13 | `docs: prepare portfolio demonstration and release notes` | Data-safe demo, evidence-linked résumé drafts, release inventory |
| 14 | `chore: prepare validated release candidate` | Clean-checkout rehearsal, CI, dependency/source audit, remaining blockers |

If step 7 has no justified optimization, commit a benchmark/decision report instead; do not change code solely to satisfy the proposed message. Every step follows the approval workflow at the top of this file.

## Acceptance

All initial-release user flows work; isolation and recovery checks pass; results can be reproduced from a clean environment; measurements include failures and limitations. Record evidence in `docs/reports/week-08-release.md` and implementation status. Unresolved required gates block release readiness, not continued independent work.

## Implementation task prompt

> Read this handoff completely, then read Plans/ENGINEERING_WORKFLOW.md, prerequisite plans, repository instructions, and implementation status. Follow every approval boundary. Work only on the first incomplete commit-sized step: propose its branch, scope, checks, and commit message, then wait for branch approval before changing code. After approval, implement and validate only that step, present the complete diff and results, and wait for commit approval. Do not work directly on main, push, open or merge a pull request, or begin another step without the required authorization. Keep repository language natural and project-focused, preserve unrelated work, and report actual evidence and incomplete gates.
