# Local release candidate draft

Proposed identifier: `v0.2.0-rc.1`. This is a documentation label only; no tag,
release, deployment, push or commit has been created by this batch. Candidate
status: **not validated and not ready to publish**.

The workspace combines authenticated private collections, immutable retrieval
snapshots, sparse/dense/hybrid comparison, grounded saved research runs and exports.
The Weeks 7–8 branch adds safe operational events, recovery/isolation scenarios,
bounded load tools, shared heavy-worker admission, paired quality reports, citation
keyboard focus and offline backup/rehearsal tools. No new throughput or quality
claim is supported until the deferred runs are completed.

## Five-minute demonstration draft

1. Use two dedicated demonstration accounts and synthetic fixture text. Keep private
   browser tabs, environment variables, filesystem paths and session files off-screen.
2. Upload the synthetic source into a private collection. Show durable job stages and
   the resulting snapshot. Explain that activation publishes a complete snapshot.
3. Compare sparse, dense and hybrid retrieval for one preselected, reviewed question.
   Show their separate scores without presenting unlike scores as directly comparable.
4. Request a cited answer from the exact pinned demonstration model. Inspect a source
   with the keyboard, close with Escape, and show the saved run's snapshot/model.
5. Show a deliberately unsupported question and an honest limitation: structural
   validation cannot establish factual support. Do not substitute a fabricated answer
   if the model fails. Display the failure and retain search as the useful fallback.
6. Download JSON or Markdown, reopen the saved run, then switch to the second account
   and demonstrate denial of the private run/export. End without publishing data.

The current real-model review packet remains pending. Rehearse on approved data and
record the exact model revision and configuration before recording a public demo.

## Source and license inventory for review

| Material | Repository record | Release action still required |
|---|---|---|
| Project source | Root `LICENSE` | Confirm intended terms and included notices |
| Python libraries | `python/pyproject.toml`, `python/requirements-dev.txt` | Review licenses and current advisories for exact pins |
| Go libraries | `engine/go.mod`, `engine/go.sum` | Review transitive notices and advisories |
| Browser libraries | `web/package.json`, `web/package-lock.json` | Review transitive notices and advisories |
| MiniLM embedding model | `python/src/retrievec/dense/model.py` revision | Verify upstream terms for the downloaded artifact |
| Generation model/runtime | `docs/reports/week-06-model-smoke-v2.json` | Verify model/runtime licenses; do not bundle weights |
| Seed papers | `datasets/manifests/seed-papers-v1.json` provenance/license notes | Verify each paper's distribution permission; keep local full text private |
| Synthetic fixtures | `datasets/fixtures`, `datasets/evaluation` | Label synthetic evidence; remove accidental private additions |
| User uploads, sessions, backups | Ignored `private/`, `artifacts/` | Exclude from repository, demo and release packages |

This inventory is a review queue, not a completed legal/security audit. No third-party
license or current security-guidance claim was newly verified in this batch.

## Résumé drafts without unsupported numbers

- Built a Go/Python research workspace with immutable retrieval snapshots, hybrid
  ranking, authenticated private collections and citation-linked saved answers.
- Implemented leased ingestion, fenced publication, cancellation/revocation handling
  and reproducible evaluation tooling with explicit failure accounting.
- Add a measured performance bullet only after the controlled workload archive is
  available; link the exact report/configuration and include corpus size and failures.

## Acceptance record required before publication

- Clean checkout installation and required Go/Python/frontend checks, PostgreSQL
  integration and browser tests; supported Windows/Linux interruption runs.
- Real local OIDC smoke, two-user historical source/run/export/reconnect revocation,
  prompt-injection/model-output cases and keyboard/mobile inspection.
- Repeated complete-workflow measurements, mixed-load fairness/memory observations,
  baseline-derived budgets and any optimization's ranking parity.
- Fresh frozen reviewed retrieval labels and actual human answer acceptance.
- Isolated restore rehearsal with ownership, referenced artifacts, saved-run replay
  and fresh authentication verified after restore.
- Dependency security guidance/advisory review against official upstream sources,
  source/license/private-data audit and final owner approval for release actions.

Record actual results in [week-08-release.md](reports/week-08-release.md). An unchecked
gate blocks release readiness; it does not justify inventing evidence or publishing.
