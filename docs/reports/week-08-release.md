# Weeks 7–8 implementation record

Base: `f82a49c6f9eeacf8dbc865c5235413ddee745a15` on main. Weeks 5–6
implementation is present through PRs 16–23. This working batch is intentionally
uncommitted on `feat/workspace-hardening`. Broad tests, load runs, restore
rehearsals and release actions are deferred at the owner's request.

## Prerequisite inventory

| Flow | Implementation and existing evidence | Remaining gate |
|---|---|---|
| OIDC/session/CSRF | `app/auth.py`, signed issuer tests, prior browser CI | Real local Keycloak smoke |
| Upload → activation | `app/uploads.py`, `registry/worker.py`, real browser CI | Process interruption and mixed-load rehearsal |
| Snapshot-pinned sparse/dense/hybrid search | `dense/hybrid.py`, generated RPC, prior integration CI | Controlled hardware baseline and fresh judgments |
| Generation → validated saved run | `app/research_worker.py`, real Qwen smoke records | Human semantic review; provider quality still limited |
| Citations, replay, cancellation, exports | `app/research.py`, `app/exports.py`, prior browser CI | Expanded failure/revocation and reconnect coverage |
| Initial release | Local setup and week-06 report exist | Backup/restore, source audit, accessibility review, clean-checkout rehearsal |

Historical CI evidence: [final week-06 checks](https://github.com/VEDLEGENDARY/RetrieVec/actions/runs/35541561924).
That run does not validate this uncommitted batch. No human review is fabricated;
the owner explicitly deferred the twelve-answer review packet.

## Decisions

Keep artifact garbage collection disabled. Preserve saved-run snapshot/source
references. Do not optimize retrieval without a measured baseline and rank-parity
evidence. Do not publish, tag, deploy or change repository visibility in this batch.
New regression scenarios and operational tools will be supplied for later execution.

## Implementation delivered in this working tree

| Step | Authored work | Still needed |
|---|---|---|
| 1 | Prerequisite inventory and regression scenarios | Run current acceptance suite |
| 2 | Allowlisted Python/Go JSON events, request metadata, migration 007 stage clocks | Integration correlation/redaction exercise |
| 3 | Activation lock-order fix, kill-before/after-publication, lease/attempt/CAS tests | Execute on supported platforms; Go restart/DB outage rehearsal |
| 4 | Cancellation, monotonic persisted events and late-publication scenarios | Real provider interruption and reconnect rehearsal |
| 5 | Two-user cached history/citation/export/reconnect revocation scenario | Execute database/browser isolation suite |
| 6 | Four bounded load profiles, warmup/raw outcomes, latency/errors, optional CPU/RSS sampling | Owner hardware baselines and variability-derived budgets |
| 7 | Decision: no speculative optimization | Choose bottleneck only from measured evidence |
| 8 | Shared heavy-worker slot, combined queue admission, consistent lock ordering | Mixed-load fairness, memory and outage behavior |
| 9 | Paired query bootstrap and reviewed-set freezing with exposure checks | Fresh actual labels and human answer review |
| 10 | Citation focus/return/Escape, stale inspection protection, busy form/history controls | Keyboard/mobile/browser inspection |
| 11 | Offline bundle, hashes, fresh-target restore, metadata/ownership fingerprints, session exclusion | Isolated PostgreSQL/artifact restore rehearsal |
| 12 | Benchmark and recovery commands with limits | Executed reproduction records |
| 13 | Data-safe demo, release/license inventory, résumé drafts | Rehearsal and source/license verification |
| 14 | Local candidate identifier and explicit release gates | Clean checkout, CI and security/source audit; no release authorized |

Implementation guides: [operations](../workspace-operations.md),
[benchmarks](../workspace-benchmarks.md), [architecture decision](../architecture/0007-workspace-hardening.md),
[candidate draft](../release-candidate.md).

Editing-time results: Ruff formatting/lint passed for the 28 changed/new Python files;
the frontend passed `tsc --noEmit`; changed Go files were formatted with `gofmt`;
`git diff --check` passed. These are not behavioral acceptance results.
No new unit/integration tests,
browser runs, benchmarks, model calls, backup or restore executions were performed
in this batch. Previous CI results must not be cited as validation of these changes.

## Outstanding acceptance

Release readiness is **pending**. All new implementation and authored test cases
must be exercised before acceptance. Human judgments, measured load budgets and
isolated restore evidence are required; scaffolding is not a completed gate.
