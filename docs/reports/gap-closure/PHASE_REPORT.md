# Stage 1 implementation report

Updated: 2026-10-01. Branch: `feat/openapi-contract`, PR #46. Stage 2 has not started and requires review, as requested.

## Changes

- Removed unvalidated model text from the browser and event publication. Old stored draft events return redacted payloads. Stages and retained evidence still stream; final answers still require source and structural checks.
- Corrected scientific-prose false positives while rejecting tags, comments, executable schemes and data URLs. Added 22 table cases and an invalid-provider browser regression.
- Cleared foreign-principal device drafts on authentication, enforced expiry in the memory fallback, and tested expiry/logout/collection isolation. Saved research remains server-owned and reauthorized.
- Added collection/view/run fragment URLs with history/reload support, server-side bounded follow-up context expansion, editable search query, and named Evaluate controls. Stage events trigger authorized status refresh, with polling fallback.
- Extracted citation/types/ranking presentation; added CI token lint and automated accessibility scans. New dev dependency `@axe-core/playwright` 4.13.0, MPL-2.0, enables the requested axe scans; it is not shipped as application code. See [Playwright accessibility guidance](https://playwright.dev/docs/accessibility-testing) and [package license](https://github.com/dequelabs/axe-core-npm/blob/develop/packages/playwright/package.json).
- Reused immutable artifact loads within a comparison request and added deterministic partition-based top-k. Recorded real tokenizer overflow measurements without silently changing existing chunk identities/defaults.

## Verification

Local Windows `python scripts/check.py` passed: Go vet/test/build, dependency compatibility, Ruff, formatting, and 115 Python tests with 19 environment-dependent skips. No local PostgreSQL service/DSN was available. `python -m retrievec.contracts --check` passed. Frontend production build, 15 UI tests and Prettier passed. Axe found no serious/critical issues in the tested light/dark views, dialogs/navigation and evidence pane. Native screen-reader behavior remains unmeasured.

All implementation checks passed at `1be7933ebb8bec8e9bf3ffaaec18405d6e9ae7eb`, verified 2026-10-01: PostgreSQL/RPC integration (including the invalid-answer and keyboard browser workflow), Linux race checks, Windows checks, and container/installed-frontend checks. Stage 1 is ready for review with the HTTP measurement limitation below; it is not a claim that every measurement gate is complete.

## Measurements and deviations

At the pinned MiniLM tokenizer, both retained 256-analyzer-token snapshots overflowed on 160/193 chunks (82.90%). A fresh 96-analyzer-token import overflowed on 0/467; maximum 244 wordpieces. These are local seed-corpus results, not universal bounds. `wordpiece-budget.json` records snapshot IDs, tokenizer hash, counts and quantiles. Oversized input is explicitly rejected before inference.

No before/after authenticated HTTP search/answer latency measurements were made: the local service/database fixture is unavailable. Existing synthetic browser and small real-model transport timings remain in [PERF.md](../../design/PERF.md) with their limits. No speedup or human quality labels are claimed.

Follow-up rewriting deliberately uses one original parent question as bounded context, with no generated facts or extra model charges. It is not a learned pronoun resolver. Authorization and configured-provider consent are checked before preview and enqueue. Token budgets still apply downstream. Cross-request artifact caching is deferred; request-scoped reuse avoids retaining another principal's data or bypassing artifact checks across requests. Larger controller files have explicit architectural exceptions in GAP_AUDIT.md.

## Risks and three follow-ups

1. Finish the representative authenticated HTTP measurement gate before declaring full closure. Establish a stable corpus/model/workload for p50/p95; do not substitute synthetic UI timing.
2. Review deterministic follow-up quality and the controller-size exceptions. Approve a model-based rewrite study or controller state-machine refactor only as separately measured work.
3. After Stage 1 review, start Stage 2.1 on its own branch: real SciFact/SCIDOCS pipelines, frozen development tuning grid, held-out results and bootstrap intervals. Do not start later Stage 2 tasks in the same session.

Matched production-browser follow-up (30 synthetic samples per build): baseline/updated readiness p50 96.4/93.3 ms, p95 126.9/125.9 ms; observed search p50 77.9/75.0 ms, p95 97.4/99.2 ms. Mixed small differences do not establish a speedup. These include automation observation overhead and are not HTTP retrieval or answer-run latency.

