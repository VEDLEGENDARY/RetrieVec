# Repository closure and workspace refinement — 2026-10-06

The inventory examined all 51 historical PRs and the one repository issue using
the authenticated GitHub API, including comments, reviews and check runs. The
only inline feedback was seven threads on merged PRs #1 and #3. Open PRs #49–52
had no inline comments or substantive code-review findings; #49 had a Copilot
quota notice, which is not a completed review. Review summaries on #1, #3 and #4
also contained five suppressed findings, assessed below. No PR was merged, squashed, rebased,
force-pushed or discarded during this work.

## Dispositions

| Item | Finding and action |
|---|---|
| Issue #2, workspace scaffold | The scaffold was restored and is present on main. Go/Python layout, package install, checks and Windows/Linux CI exist. Current Go vet/tests/build and Python checks pass. Closed as completed. |
| PR #1, four roadmap threads | Their historical paths no longer exist in the current tracked repository. The broken onboarding paths are obsolete; do not restore unused roadmap documents. Resolved as obsolete. |
| PR #3, UTF-16 comment | The proposed compile error is incorrect. `go doc unicode/utf16.EncodeRune` confirms `(r1, r2 rune)`; the existing implementation compiles and Go checks pass. Resolved with no code change. |
| PR #3, audit path containment | Still valid: a manifest could point outside the declared source root. The fix resolves the real path and rejects files outside the root before reading. A real-import regression reproduced both relative and absolute escapes, then passed after the fix; thread resolved. |
| PR #3, implementation-status summary | That historical status document is absent on current main. Current design, benchmark and release records supersede it. Resolved as obsolete. |
| PR #3, suppressed UTF-8 finding | Reproduced invalid start/end byte offsets inside a multibyte character. Reject continuation-byte boundaries with `CorpusError` before chunking; valid Unicode offsets and engine fixtures pass. |
| PR #3, suppressed canonical-number finding | Reproduced Go accepting a manifest configuration containing `-0`, although Python canonicalizes it to `0`. Require canonical decimal spelling for configuration integers. Valid zero and negative integers pass; snapshot encoding, identities and published artifacts remain unchanged. |
| PR #3, suppressed CLI-copy finding | Replaced the obsolete future-command description. Actual `python -m retrievec --help` now describes the implemented import, validation, capture and evaluation commands. |
| PR #1, suppressed missing-workflow-input finding | The old workflow/status-file pair is absent on current main and superseded by current records. No unused historical files were restored. |
| PR #4, suppressed revert-path finding | Historical revert/roadmap naming is superseded by subsequent restoration and removal of those paths. No old commits or history were rewritten. |
| PR #49, Kubernetes path | Latest four checks were green and the PR is mergeable. Live cluster verification remains unavailable: `kubectl config current-context` reports no context. Keep open for review. |
| PR #50, retrieval experiments | Latest five checks were green. Preserve opt-in configurations and the published rejection decision. Human PDF passage judgments and end-to-end optional layout-adapter evaluation remain open. Keep draft. |
| PR #51, answer/workspace polish | Latest five checks were green. Preserve blank human-review fields and automatic-only/synthetic labels. Keep draft and preserve its stack on #50. |
| PR #52, release work | Reproduced OpenAPI drift on both platforms. Published the existing section fields and PDF route, documenting its actual binary PNG response. Added committed-contract and response-type regression checks. All five latest checks are green at `9b71156`, including Linux/Windows, container, PostgreSQL/RPC and the model subset. Keep draft. |

The new `codex/material-workspace` branch started at main and retains #52 through
regular local dependency merges. Its new PR targets #52's branch to keep the
review focused. Existing feature commits and their original author dates remain
intact. PR #52 contained 30 separate commits before the two contract corrections;
the profile graph did not indicate a squash.

## Changes

- `scripts/audit_import.py`, `python/tests/test_import_audit.py`: root containment
  and a regression using retained source bytes with matching hashes.
- PR #52: `python/src/retrievec/app/evidence.py`, `python/tests/test_contracts.py`,
  `contracts/openapi.json`: contract metadata and drift protection.
- `python/src/retrievec/corpus/analyzer.py`, `python/tests/test_analyzer.py`,
  `engine/internal/corpus/snapshot.go`, `snapshot_test.go`: validated UTF-8 byte
  boundaries and canonical configuration integers; both reproduced before fixes.
- `python/src/retrievec/cli.py`: accurate help for implemented commands.
- `web/src/tokens.css`, `web/index.html`: semantic light/dark material roles,
  typography, elevation and spring motion; regenerated browser theme colors.
- `web/src/WorkspaceChrome.tsx`, `main.tsx`, `ui.tsx`, `style.css`: modular header,
  destination navigation, optional glass Surface, responsive layouts and removal
  of empty/dead selectors. Domain retrieval/upload/research workflows stay in
  their existing modules.
- `web/ui-tests/materials.spec.ts`, `design-system.spec.ts`: explicit material
  preferences and complete inventory/reflow verification.
- `web/demo-tests/demo.spec.ts`: captures use the isolated demo output directory.
- Design and maintenance documentation records the actual coverage and limits.

## Commands and results

| Command | Actual result |
|---|---|
| `python -m retrievec.contracts --check` | Reproduced failure; passed after generated contract review. |
| Contract unit tests | Two passed after the PNG metadata correction; the new test failed before it. |
| Import-audit regression | Both escapes reproduced before the fix; valid import and rejection assertions pass afterward. |
| `python scripts/check.py` with isolated PostgreSQL/pgvector test DSNs | Final run: 149 tests, no skips; Go vet/tests/build, dependency check, Ruff lint/format and token guards passed. Initial lint/format findings were fixed and the full command rerun. |
| Analyzer boundary regression | Both malformed UTF-8 start/end offsets failed before the fix; all three analyzer tests passed after it. |
| Canonical integer regression | Real copied snapshot with `-0` was accepted before the fix; after it, noncanonical zero is rejected and canonical zero/negative integers remain valid. |
| `python -m retrievec --help` | Passed; lists the four implemented workflow commands with accurate descriptions. |
| `npm run build` | Passed; existing Lucide module-directive warnings remain. |
| `npx prettier --check src ui-tests playwright.ui.config.ts` | Passed. |
| `npm run test:ui -- --workers=2` | 33 passed; 144 inventory captures across four viewport/theme conditions. |
| Material tests | Three passed. The first pointer test was suppressed by the host's reduced-transparency preference; explicit test emulation exercised both the material and fallback paths. |
| `docker compose -f compose.demo.yaml --profile demo up --build -d` | Rebuilt and started successfully; existing data/settings/cache volumes retained. |
| `npx playwright test --config playwright.demo.config.ts` | One real-service test passed: Keycloak registration, OIDC sign-in, preloaded default hybrid search and sign-out. Screenshot output is now isolated from the fixture inventory. |
| `go doc unicode/utf16.EncodeRune` | Confirms two returned runes; historical compile-error suggestion declined. |
| `kubectl config current-context` | No context; no live cluster claim. |

The ten guarded contrast checks passed in all four inventory conditions. Light
footer/code/error/status ratios were 6.11/6.68/7.64/6.31; dark were
9.94/8.51/8.72/7.18. Light/dark focus ratios were 7.09/9.31. These measurements
cover named rendered surfaces, not arbitrary retained images or full WCAG conformance.

The added unfocused-control check reproduced a 2.05:1 light-mode border failure.
Dedicated semantic control-border tokens now measure 3.37:1 light / 4.26:1 dark
in both resting and hover states. The selected destination's real visible border
measures 7.09:1 light / 9.31:1 dark; it also has a distinct weight. The complete
build, 148-test repository check, 33-test UI suite and real demo test were rerun
after this correction. The README capture is framed from the top of the workspace.

On Windows, the installed npm/npx Node entry points were used because the shell
shim is broken. The unchanged isolated-database runner supplies private DSNs to
`scripts/check.py`; credentials stay in ignored local artifacts. Fixtures and
screenshots are labeled synthetic and do not measure retrieval or answer quality.

## Remaining review gates

Human answer/PDF review, manual screen-reader and browser-zoom review, other
browser engines, live Kubernetes, production load and disaster-recovery rehearsal
remain unverified. Qwen failure accounting and benchmark measurements were not
rerun or relabeled. No retrieval default, authorization, cloud consent, retained
source policy, snapshot identity or API error code changed. Skills, AGENTS,
credentials, model weights, `.env` files and paper PDFs were not staged.

## Suggested PR description

Research navigation now uses a modular collection header and adaptive material
surfaces, with solid evidence reading areas, semantic light/dark colors and
damped-spring control feedback. All three destinations reflow at 320px with
doubled text, and material effects respect reduced motion, reduced transparency
and forced colors. A historical import-audit root escape is fixed with a real
regression. Existing domain workflows, consent and snapshot semantics are preserved.

Validation: 149 Python tests without skips, Go vet/tests/build, web build, formatting
and all 33 UI tests passed. The inventory covers 1280px/390px and both themes.
The rebuilt Docker demo passed real Keycloak sign-in, hybrid search and sign-out.
Manual assistive-technology, other-browser, live-cluster and production-load gates
remain open. This PR is draft and stacked on #52; retain separate commits and do
not merge without owner review.
