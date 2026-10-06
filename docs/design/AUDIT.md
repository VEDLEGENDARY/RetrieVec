# RetrieVec UI/UX consistency audit

Date: 2026-09-29  
Baseline: `f6e021142df2f4a4990b7b4c2b28da45bd485882`  
Plan: **Plan 1, Step 1 only**  
Status: **UI unification implemented on `codex/ui-unification`, based on `origin/main` (`8384565`). The original inventory below is historical; the implementation update records current coverage and remaining verification limits.**

## Implementation update — 2026-10-04

See [the design-system contract](docs/DESIGN_SYSTEM.md) for the shared APIs, token roles, static asset generation, and reproduction commands. This phase changes presentation and browser tests only; retrieval defaults, storage, authorization, consent, snapshot immutability, and API error codes are unchanged.

| Findings | Current implementation |
| --- | --- |
| DS-01–06 | One token source, complete semantic light/dark roles, six named type sizes, 4px spacing scale, five radius roles, shared elevation and explicit disabled colors. |
| DS-07–08, DS-30 | Native `color-scheme`, generated theme-color metadata, supported system/serif/monospace font stacks, explicit small/heading/code/placeholder roles. Inter is not assumed. |
| DS-09–10 | Standard control icons and icon-button sizes, accessible icon-only names, decorative icons hidden; trailing action-arrow copy removed. Source SVG geometry and keyboard notation are retained. |
| DS-11–12 | Focus outlines remain visible; disabled controls do not receive enabled hover styles. Rendered input-focus and disabled-hover assertions cover both themes. |
| DS-13–15 | Shared loading/busy controls, persistent Notices, and Fields with label/help/error associations. Upload queue errors now associate with the file control; retry keys and validation limits are unchanged. |
| DS-16–17, DS-20 | Shared Button/ActionLink/IconButton, Surface, EmptyState/LoadingState, StatusBadge, Disclosure, and native-dialog base. Native control sites are centralized in `ui.tsx`; domain workflows and nonmodal inspectors retain their behavior. |
| DS-18–19 | Removed obsolete overview/hero/stat/workflow, tooltip, old citation-inspector, navigation-open, status, and `rise` rules; merged repeated eyebrow/inspector/excerpt declarations. Shared 150–250ms motion and reduced-motion override remain. |
| DS-21–28 | Cited answers and Saved research are distinct; consistent source actions and sentence case; explicit readable state mapping; recovery-oriented errors; readable-text/OCR wording; named export formats. Backend enums and error codes are unchanged. |
| DS-29 | Generated favicon palette and browser chrome colors come from the token source. Structured evidence uses a tokenized highlight with a contrasting halo; ordinary PDF exact highlighting is not claimed. |

### Phase 2 navigation — 2026-10-04

The three destinations are **Ask, Sources, and Saved research**. Overview capabilities remain in onboarding, collection readiness/access, and collection details. Ask chooses Answer automatically only after the collection's authorized provider response confirms a consented provider; otherwise Find passages explains the missing setup/consent. An explicit mode choice survives late provider responses. Provider requests abort on collection/session changes. Opening an existing run is an explicit history action, not permission to generate.

More disclosures contain search configuration, answer options, result filters/diagnostics, shortlist, and run provenance/replay. The model and Local/Cloud indicator remain visible in Ask. Cmd/Ctrl+Enter works in both modes, ignores IME composition, and checks readiness/consent before submitting. No consent is granted by navigation, provider selection or a shortcut.

Quick actions index destinations, upload/composer focus, comparison and syntax, filters, recent queries, excerpt display, passage inspection, shortlist/export, provider/follow-up, saved lookup/conversations, four answer exports, replay and provenance. Selecting an action opens enclosing native disclosures and focuses the relevant control; it does not trigger export or paid generation. Missing prerequisites produce an explanation. [Current activation counts](CORE_FLOWS.md#current-feature-map-and-click-counts) include native-select steps and identify quick-action alternatives to deeper paths.

The shared **Based on** control distinguishes actual claim/comparison citations from other retained retrieved candidates. Search results are explicitly identified as retrieved passages, not generated-answer evidence; shortlist membership never becomes a citation.

Saved lookup reuses the existing collection-authorized, owner-filtered, cursor-paginated endpoint (default 50, maximum 100). No backend authorization/storage/API changes were made. UI fixtures cover collection scope, pagination, no per-conversation fanout, and denied responses; real database policy execution remains unverified on this host.

The phase-2 verification record is [navigation-phase-2-2026-10-04.json](docs/results/navigation-phase-2-2026-10-04.json): `scripts/check.py` passed (106 Python tests executed; 19 existing PostgreSQL skips; Go checks passed), `npm run build` passed, and `npm run test:ui -- --workers=2` passed all 29 tests. The inventory produced 144 captures across 1280/390px and light/dark, including the new disclosure/evidence states. Shortlist feedback, cancellation messages and Undo remain outside collapsed disclosures. The phase-1 results below remain historical. Manual screen-reader, real-service, non-Chromium, and human visual-approval gates remain open.

### Current screen coverage

`web/ui-tests/design-system.spec.ts` captures the current equivalents of every application-owned inventory row at **1280px and 390px, light and dark**, including errors, empty/loading states, disabled/selected controls, all four structured-evidence bodies, processing/run states, provider consent, source previews, and overlays. PNGs and `screen-and-contrast-report.json` are saved under `web/test-results/design-system-screen-inventory-<width>-<theme>/` and attached to Playwright results. Fixtures are explicitly synthetic, not model-quality evidence. They are captures, not approved golden-image baselines.

The standalone overview and browser archive-confirmation screen had already been replaced on `main`; captures cover Collection details/readiness and archive Undo. Mobile navigation is captured at 390px; its desktop equivalent is the persistent sidebar. External OIDC-provider pages are outside this repository's UI and are not represented as tested screens.

The suite runs WCAG-tagged axe scans against each settled fixture screen in both themes. It also measures computed foreground and composited background colors for answer/status badges, file errors, diagnostic code, footer, focused skip links, and input focus. The historical stat-detail surface was removed with the obsolete overview. The measurement helper rejects gradient/image/opacity text surfaces instead of guessing a passing ratio. Source images use their own retained colors; no arbitrary-image highlight contrast certification is claimed.

Supplemental checks cover forced-colors focus, reduced motion, and 640px reflow. Existing tests cover shortcuts, focus return, Escape, upload retry keys, drafts, session cleanup, and streaming revocation. Manual screen-reader testing, actual browser zoom, other browser engines, and real-service/OIDC integration remain unverified. PostgreSQL integration tests require an isolated PostgreSQL 18 service; Docker's Linux-engine pipe is unavailable on this machine, including outside the sandbox. Do not treat automatic database-test skips as passed integration gates.

The remaining sections preserve the original source audit and its exact baseline values for comparison. Historical statements such as “no shared library” or “not applied” below describe `f6e0211`, not the current implementation.

### Verification results — 2026-10-04

Measured records: [UI screen/contrast report](docs/results/ui-unification-2026-10-04.json). Both viewport sizes produced the same ratios below; values are rounded to two decimals only for this table.

| Rendered surface | Light | Dark | Minimum |
| --- | ---: | ---: | ---: |
| Answer/status badge | 6.31:1 | 7.18:1 | 4.5:1 |
| Upload file error | 7.64:1 | 8.89:1 | 4.5:1 |
| Diagnostic code | 6.37:1 | 8.50:1 | 4.5:1 |
| Footer | 5.92:1 | 10.01:1 | 4.5:1 |
| Focused skip link | 7.09:1 | 7.09:1 | 4.5:1 |
| Input focus outline against field surface | 7.09:1 | 9.50:1 | 3:1 |

The new skip-link assertion first failed at **1.43:1** in dark mode; using the shared action background fixed it. Historical stat-detail styles are removed, so there is no surviving stat-detail surface to certify.

- `python scripts/check.py`: exit 0; Go vet/tests/build and Python dependency/lint/format/token checks passed. Python reported 125 tests, with **106 executed and 19 automatically skipped** for the unavailable isolated PostgreSQL service.
- `cd web && npm run build`: exit 0; generated-brand consistency and TypeScript checks passed. Dependency-level Lucide `use client` warnings remain.
- `cd web && npm run test:ui -- --workers=2`: **19 passed**, including all four screen matrices, with **124 PNG captures**. Settled inventory fixtures have no violations from the selected WCAG axe rules. Loading, forced-colors and supplemental reflow captures have their explicitly scoped assertions rather than a claim of full axe certification.
- `docker info --format '{{.ServerVersion}}'`: failed because the Docker Desktop Linux engine pipe does not exist, including on the escalated retry. Database/integration checks remain unverified; no test skip conditions were changed.

On this Windows host, Python used `.venv/Scripts/python.exe`; npm used `node C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js`. Generated screenshots/logs remain local and ignored. These checks establish fixture behavior and measured contrast, not full WCAG conformance or release performance.

## Scope and method

Reviewed every authored UI module in `web/src`, the complete `style.css`, HTML entry point, favicon, browser-test definitions, public API error envelope, and README terminology. The local `skills/design-system.md`, `skills/design-critique.md`, `skills/frontend-design.md`, and `skills/accessibility-review.md` inform the recommendations. Those local guidance files remain excluded from Git.

This is a source audit, supported by the desktop/mobile/light/dark screenshot review and browser checks performed for the baseline release. No new complete screen-reader audit or state-by-state visual certification was performed for this document. Findings below distinguish definite source inconsistencies from checks still required. Appendices enumerate authored values and JSX sites; repeated runtime instances are not counted as separate components. Third-party source and generated Tailwind defaults are excluded from literal counts, but browser/Tailwind inheritance is noted where it affects the design system.

### Inventory totals

| Category | Measured inventory | Meaning |
| --- | --- | --- |
| React render functions | 9 | App, Search, Uploads, Research, AdvancedEvidence, Structure, CommandMenu, NavigationPanel, EvidenceTray |
| CSS entry points | 1 | `web/src/style.css`, importing Tailwind |
| Custom property names | 16 | 25 distinct name/value definitions including dark overrides; not a complete token system |
| Color literals | 100 | Distinct CSS spellings including alpha colors and transparent; includes token definitions, not 100 intended semantic colors |
| Font-size declarations | 24 unique values | Includes four fluid expressions and one `em` value; exceeds the requested maximum of six sizes |
| Font-family declarations | 2 unique values | System/Inter stack and Georgia/serif; monospace and some smaller elements also inherit browser/Tailwind defaults |
| Line heights / weights / tracking | 6 / 4 / 6 unique values | No named type roles |
| Spacing declarations | 105 unique property/value pairs | Shorthands retained; this is not a claim that there are 105 spacing scales |
| Radii / shadow declarations | 16 / 13 unique values | Shadows include token references and `none` |
| Authored buttons / fields / links | 32 / 13 / 5 sites | Fields: 6 inputs, 5 selects, 2 textareas; mapped controls create more runtime instances |
| Dialog / disclosure / aside sites | 2 / 7 / 4 | Two asides are alternate desktop/mobile navigation renderings |
| Icon library | 1 | Lucide React; 33 explicit-size usage sites, plus text glyphs and an evidence-region SVG |
| Icon sizes | 10 | 14, 15, 16, 17, 18, 19, 24, 28, 30, 32 CSS pixels |

## Screen and state inventory

There is one application shell with conditional views rather than separate page routes. Each row includes the states that must retain their behavior through the later refactor.

| Screen or surface | Source | States and child patterns |
| --- | --- | --- |
| Opening workspace | `web/src/main.tsx:94` | Plain status message while session/collection requests complete |
| Signed-out welcome | `main.tsx:99` | Brand mark, headline, sign-in link, optional global error, private-workspace explanation |
| Empty workspace | `main.tsx:434` | No active collection, decorative symbol, collection-creation guidance |
| Persistent workspace shell | `main.tsx:130` | Filtered collection list, selected collection, empty filter, create form, account actions, breadcrumb, header, archive action, global error, section navigation, footer |
| Collection overview | `main.tsx:320` | Empty/active snapshot, private/curated access, hero action, three status cards, three-step workflow |
| Sources | `Uploads.tsx:156` | Owner/read-only access; empty queue; dragging; selected/invalid files; batch limits; sending; unconfirmed retry; queued/running/retry/succeeded/failed/cancelled processing |
| Search | `Search.tsx:129` | No snapshot, empty question, free-text/Boolean syntax, retrieval selection, searching/cancelled/error, prior results retained |
| Search results | `Search.tsx:282` | Method filtering, text filtering, no matches, full/compact excerpts, active passage, original ranks, snapshot diagnostics |
| Recent searches | `Search.tsx:235` | Disclosure, up to five in-memory query/configuration recalls |
| Evidence shortlist | `EvidenceTray.tsx:15` | Empty/filled/full, selected/unselected passages, comparison cards, remove, JSON download, per-passage provenance |
| Search evidence inspector | `Search.tsx:454` | Inline nonmodal aside, keyboard dismissal/focus return, original source link/preview/error, structured evidence, unavailable original |
| Cited answers | `Research.tsx:342` | New/existing conversation, question/follow-up, no provider, local/cloud provider, consented/revoked/read-only consent, submitting |
| Saved answer/run | `Research.tsx:461` | History selection, reconnecting/offline/retry, queued/retrieving/generating/validating/failed/cancelled/completed, claims, citations, comparisons, limitations, export, replay, provenance |
| Citation inspector | `Research.tsx:609` | Fixed nonmodal aside, reauthorized evidence, text close control, focus return, source availability, structured evidence |
| Structured source evidence | `AdvancedEvidence.tsx:144` | Loading/unavailable, source image and located rectangle, review/derivation/warnings, synthesis excluded, original PDF, raw extraction disclosure |
| Structured evidence body | `AdvancedEvidence.tsx:51` | Prose; tables with merged/missing/ambiguous/partial cells and footnotes; equation text/definitions; figure observations/uncertainty |
| Quick actions | `CommandMenu.tsx:11` | Native modal, query, selected option, no matches, keyboard shortcut/navigation, pointer selection, close/backdrop |
| Mobile navigation | `NavigationPanel.tsx:4` | Responsive native modal, focus containment, Escape/backdrop/close, scroll lock; desktop uses a sticky aside |
| Archive confirmation | `main.tsx:65` | Browser-owned `window.confirm`; cancel/confirm, retained-files warning, pending archive |
| External authentication | `/auth/login` and OIDC provider | App owns initiation/callback/errors, but the external identity-provider screen is outside this design system |

## Component and style inventory

### Existing React boundaries

`App` owns shell/view composition and create/archive actions; `useWorkspace` owns session and collection request lifetime; `api` owns HTTP response handling. Search, Uploads, and Research own their workflows. AdvancedEvidence/Structure, EvidenceTray, CommandMenu, and NavigationPanel are domain or interaction components. There is **no shared Button, Field, Card, Dialog, Notice, EmptyState, Tooltip, Toast, or Skeleton component library**. Absence alone is not a defect: create primitives only where existing patterns need consolidation.

### Button and link presentations

| Family | Current implementation | State coverage / inconsistency |
| --- | --- | --- |
| Base action | Global `button, .button` | Shared hover/focus/disabled styles; no consistent pressed/error/loading API |
| Primary action | `.primary`, `a.primary` | Search/upload/generate/sign-in; loading communicated by individual callers |
| Quiet action | `.quiet`, `.quiet.citation` | Archive and citation chips share a name despite different purpose and spacing |
| Collection selection | `.collection`, `.collection.selected` | `aria-pressed` plus custom selection colors |
| Section navigation | `.view-tabs button`, `.active` | `aria-current="page"`; distinct treatment from other selection controls |
| Result selection | `.hit`, `.hit.active` | Card-like button, selected passage styling |
| Shortlist toggle | `.shortlist-action[aria-pressed]` | Separate size/padding/selected styling |
| Command controls | `.command-trigger`, `.command-result.selected` | Trigger, option and close control; selected options use listbox semantics |
| Icon controls | Mobile close/open, inspectors, shortlist remove, queue remove | Shared global height but inconsistent width, padding, icon size and visible labeling |
| Workflow actions | Run history/export/replay/consent; recent-search buttons | Mostly classless buttons arranged with one-off containers |
| Source links | `.button.source-link`, plain anchors in Research/AdvancedEvidence | Same external-source task has button vs plain-link treatment and inconsistent arrows |

These are presentation families, not claims that every different purpose should look identical. The target library should expose intentional variants and preserve button versus link semantics.

### Cards, feedback, fields, overlays and disclosure

| Pattern | Current variants | Consolidation opportunity |
| --- | --- | --- |
| Cards/surfaces | Hero, overview stats, workflow, empty, uploads, search form, ranking, inspector, answer, consent, comparison, shortlist, shortlist passage, recent searches, command dialog | Shared surface/border/padding rules plus explicit elevated/outlined/accented variants; domain layouts stay in domain components |
| Fields | Collection creation/filter, document input, search query/syntax/method/filter, research question/follow-up/provider/conversation, command combobox | Labels largely exist; error/help associations, disabled state and density are not standardized |
| Feedback | Global `.error`; inline plain run alerts; source errors as status; upload and export notices; `.interaction-notice`; source-loading text | Shared Notice with explicit error/success/info and announcement policy; keep blocking errors persistent |
| Status | `.status` upload badges, `.answer-status`, raw run-state text, readiness text in header | Shared status presentation and public label mapping, separate from backend enum values |
| Empty/loading | `.empty`, `.no-results`, several plain paragraphs, opening/loading status | Shared composable EmptyState and LoadingState; skeleton only if it preserves layout and announcement behavior |
| Modal | CommandMenu and mobile NavigationPanel; browser archive confirmation | Shared native-dialog foundation with purpose-specific sizing; preserve shortcut/focus/escape and destructive confirmation behavior |
| Nonmodal inspector | Inline search aside and fixed citation aside | Shared heading/close/provenance presentation; explicitly preserve nonmodal semantics unless separately approved |
| Disclosure | Recent searches, shortlist, snapshot diagnostics, run provenance, processing activity, passage provenance, raw extraction | Consistent summary spacing/icon/focus and content padding |
| Tooltip/toast | No dedicated current implementation | Do not add unused components or move essential information into hover-only help / transient notices |

## Confirmed inconsistencies and proposed remedies

Priority: **High** affects readability or hides meaning; **Medium** affects consistency/maintainability; **Low** is polish. Proposed changes are not implemented.

| ID | Priority | Evidence / inconsistency | Recommended later action |
| --- | --- | --- | --- |
| DS-01 | Medium | 16 token names cover only some colors/shadows; most style properties still use literals (`style.css`, Appendix A). | Introduce semantic color/type/space/radius/shadow/motion tokens as one source. |
| DS-02 | Medium | 24 font-size values include near-duplicates such as .67/.68/.69/.7rem and .75/.76/.78/.8/.82/.83/.85/.86rem. | Map to at most six named type roles, preserving heading hierarchy and readable metadata. |
| DS-03 | Medium | Margins/padding/gaps use .18/.2/.35/.45/.55/.62/.65/.7/.76/.85/.9rem, among many values. | Consolidate on the requested 4/8px rhythm; explicitly distinguish layout proportions from spacing tokens. |
| DS-04 | Medium | 16 radii range from .3rem to 1.3rem plus 999px and 50%; similar cards use .8/.85/.95/1rem. | Define control/card/overlay/pill/circle roles; keep true circular shapes intentional. |
| DS-05 | Medium | Named shadows coexist with literal hover, primary, logo, dialog and inspector shadows; two backdrops use different color/blur rules. | Use named elevation/backdrop tokens and document intended overlay differences. |
| DS-06 | High | Dark mode overrides only nine existing token names and leaves fixed text/status/error/detail colors. | Complete semantic light/dark maps and remove selector-specific color patches. See contrast findings below. |
| DS-07 | Medium | `index.html` has fixed theme-color; native controls have no declared `color-scheme`; browser theme treatment can disagree with the page. | Align metadata/native controls with the existing system theme behavior. No manual theme toggle required under the functionality constraint. |
| DS-08 | Medium | Inter is first in the font stack but not bundled/loaded; Georgia is used for shortlist/search excerpts while citation excerpts inherit sans-serif. | Specify supported body/evidence/code font roles and apply them consistently; do not assume Inter is present. |
| DS-09 | Medium | Icon usage has ten explicit sizes; icons coexist with `→`, `↗`, `↵`, keyboard glyphs and raw text close labels. | Use standard control/icon sizes; replace decorative action arrows consistently. Keep keyboard notation and data-region SVG meaningful. |
| DS-10 | Medium | Decorative icons sometimes have `aria-hidden`, sometimes omit it; icon-only buttons vary in size/label conventions. | Define an icon wrapper or shared control contract and audit decorative versus informative cases. |
| DS-11 | Medium | `input/select/textarea:focus` later sets `outline:none`, overriding the earlier shared focus-visible outline. | Unify focus indication without losing text-field focus feedback or keyboard visibility. |
| DS-12 | Medium | Global `button:hover` also matches disabled buttons; disabled appearance uses opacity rather than explicit semantic colors. | Exclude disabled controls from active hover styling; define disabled states per variant. |
| DS-13 | Medium | Loading states are caller-specific strings/plain paragraphs; buttons do not share a loading/busy contract. | Standardize visible labels and busy semantics while preserving validation and duplicate-submission guards. |
| DS-14 | Medium | `.error` uses a styled box, run failures use plain alerts, AdvancedEvidence unavailable uses `role=status`, and search notices have their own style. | Map error severity to a shared Notice and consistent announcement policy; preserve actionable recovery text. |
| DS-15 | Medium | File errors are visible text but not associated through `aria-describedby`/`aria-invalid`; fields elsewhere rely on native validity. | Shared Field should support labels, descriptions, error IDs, required and invalid states without changing limits. |
| DS-16 | Medium | Quick actions and mobile navigation independently implement native dialogs; citation/search inspectors and archive confirmation follow different mechanics. | Consolidate compatible modal primitives; retain explicit nonmodal and browser-confirm behavior until equivalence is tested. |
| DS-17 | Medium | Card border/background/padding is repeated across domain selectors, sometimes transparently and sometimes opaquely. | Introduce shared surface variants, with domain-specific layouts remaining separate. |
| DS-18 | Medium | `.hero-card`, `.hero-icon`, `.eyebrow`, `.inspector-heading` and entry animations receive later overrides; `.navigation.open` is not produced by current NavigationPanel. | Remove obsolete declarations after tracing computed styles; merge overrides into canonical rules. Do not delete domain components just because their layout differs. |
| DS-19 | Low | `rise` animation is declared for dashboard/uploads/research but later disabled; .16s/.22s durations and generic `transition: .16s ease` coexist. | Centralize motion and specify transition properties; preserve reduced-motion rules. |
| DS-20 | Medium | Button semantics/style are scattered over 32 JSX sites; no central variants, icon spacing, or size contract. | Shared Button/ActionLink/IconButton while preserving form types, ARIA roles, links and event handlers. |
| DS-21 | Medium | Breadcrumb says “Library”; navigation says “Collections”; search is “Ask your sources”; answers are “Cited answers”, “Ask the evidence”, and “SAVED RESEARCH”. | Apply the proposed glossary below. Preserve distinctions between search and generation. |
| DS-22 | Low | Sentence-case main labels coexist with hardcoded “SAVED RESEARCH”, “PAPER EVIDENCE”, “PAGE” and uppercase stat labels. | Sentence case for labels/headings; keep standard acronyms such as PDF, JSON, BM25 and RRF. |
| DS-23 | Medium | Raw run state (`retry_wait` etc.) can be shown in history; uploads transform underscores, answer status transforms strings differently. | Public display-label mapping for all user-visible states; do not change backend enums. |
| DS-24 | Low | “Page unavailable” vs “Page locator unavailable”; “Open original source ↗” vs “Open original source” vs “Compare original PDF page”. | Consistent availability language; shared “Open original source” action, with PDF/page context in supporting text. |
| DS-25 | Medium | Error messages differ in punctuation, specificity, recovery action and audience: “Resource unavailable”, “Request failed. Try again.”, “Check the worker”, “Select the result again to retry.” | Standard “what happened + next action” copy, retaining operator-specific details where necessary and safe API error codes unchanged. |
| DS-26 | Medium | Research says users can inspect sources “above”, but search now occupies a separate workspace section (`Research.tsx`). | Refer to the Search section by its actual label. |
| DS-27 | Medium | Upload copy says OCR “is not supported yet”, while README describes optional OCR/advanced extraction. | Say the current upload path requires readable text; distinguish configured experimental capabilities from the default UI. Verify exact wording against configuration. |
| DS-28 | Low | Export labels use raw lowercase format names (`markdown`, `bibtex`, `json`, `csv`), while shortlist uses “Export evidence”. | Use consistent action/format labels: Export Markdown/BibTeX/JSON/CSV; retain export types and filenames. |
| DS-29 | Medium | Highlight rectangle uses literal `#b04416` and stroke width 2 outside CSS; favicon uses separate greens; HTML theme-color repeats a brand literal. | Tokenize UI highlight/brand styling, retaining evidence geometry and static asset generation boundaries. |
| DS-30 | Low | Some text size/weight is implicit (`small`, `h4`, `code` family, native placeholders) rather than specified by a role. | Explicit inherited type roles so the six-size system remains enforceable after Tailwind/browser defaults. |

### Contrast findings from declared colors

These are calculated sRGB pair ratios, not a claim of a complete rendered WCAG audit. Exact opaque badge/card pairs are strong evidence; translucent surfaces and gradients need rendered checks. Normal-text target is 4.5:1.

| Pair / surface | Approximate ratio | Assessment |
| --- | --- | --- |
| `.answer-status` text `#075d50` on dark `--brand-soft: #173f35` | 1.50:1 | Definite dark badge mismatch; both colors are declared opaque |
| `.file-error` `--danger: #a64136` on dark `--surface-solid: #1b2722` | 2.52:1 | Dark-surface risk; actual queue surface uses the nearby translucent card color |
| `code` `#40534c` on dark page `#101713` | 2.22:1 | Dark diagnostics/code text needs rendered background verification and a themed foreground |
| Footer `#7a8581` on base `#f5f7f5` | 3.55:1 | Light metadata contrast risk; gradient composition can vary |
| Stat detail text `#76817d` on white | 4.03:1 | Below normal-text target even on white; small size compounds readability |

## Proposed vocabulary for Step 4 (not applied)

| Concept | Preferred public term | Keep distinct / avoid |
| --- | --- | --- |
| Whole application | Workspace | Do not use “Library” as an unexplained synonym for the collection list |
| Group of source material | Collection | Avoid Folder/Library for this same entity; no Folder UI currently exists |
| Imported document | Source | “File” remains correct during selection/upload; “paper” remains correct for scholarly content, not every .txt upload |
| Retrieved text unit | Passage | Keep chunk IDs in diagnostics/API; do not rename fields or persistence |
| Material supporting a claim | Evidence | Evidence is broader than a passage; tables, figures and equations retain their distinctions |
| Find passages | Search | Reserve “Generate cited answer” for model-backed answer generation |
| Answer section | Cited answers | Avoid competing headings “Saved research” and “Ask the evidence” for that same destination |
| Saved execution | Research run (advanced/history) | Use readable state labels; retain API identifiers and provenance terminology |
| Temporarily selected passages | Evidence shortlist | Make its temporary lifecycle explicit; do not imply saved/persistent annotations |
| Immutable corpus/index version | Snapshot | Keep exact technical meaning in diagnostics and replay actions |
| Source viewer action | Open original source | Explain page/PDF where useful without changing the destination |
| Authentication | Sign in / Sign out | Keep consistent, no Login/Logout mix in visible labels |

Error pattern: concise sentence explaining the issue, followed by a concrete recovery action where one exists. Do not invent a recovery path, expose exception details, or erase distinctions among lost access, missing originals, uncertain upload completion and temporary service failure. Keep live progress messages separate from errors. Stable API codes are not prose and must remain unchanged.

## Later-step boundaries and review checklist

Step 2 may introduce a token file and migrate literals only after this audit has been shown to the owner. A useful initial six-role type system is metadata, supporting, body, subheading, section heading, page heading; exact sizes/colors remain a Step 2 decision, not an implementation in this audit. Fluid page sizing counts as one role only when shared rather than multiplied into one-off variants.

“Replace hardcoded values” applies to design decisions, not source-page geometry, evidence coordinates, identifiers, timing of API retries, file limits, or scientific data. Border widths, focus widths, media breakpoints and icon sizes need named design constants; CSS custom properties cannot be interpolated into ordinary media-query conditions, so breakpoint handling needs an explicit supported approach rather than invalid CSS. SVG evidence coordinates must remain data-driven.

For Step 3, start with Button/ActionLink/IconButton, Field controls, Surface/Card, Notice, EmptyState/LoadingState, StatusBadge, Disclosure and a native-dialog base. Keep evidence tables, source inspectors, upload workflows and research state machines as domain components. A component should not be deleted merely because it is used once. Toast/Tooltip/Skeleton are optional implementations of actual existing needs, not a required expansion of functionality.

For Step 5, dark mode, Lucide, keyboard focus, and reduced-motion support already exist. Complete and unify them; do not claim a brand-new dark mode or replace accessible behavior unnecessarily. Manual theme controls would be an additional interaction and need scope agreement under this plan's no-functionality-change constraint.

Acceptance checks for later steps:

- Preserve session cleanup, collection boundaries, drafts across sections, temporary shortlist lifecycle, upload limits/retry keys, server authorization and immutable provenance.
- Preserve keyboard shortcuts, Escape, focus return, dialog containment, file-picker alternatives to dragging, and no-match/error paths.
- Compare every inventoried surface in light/dark mode at desktop, 390px mobile, and zoomed layouts; include error, disabled, selected and loading states.
- Validate contrast on rendered surfaces, native control theming, high-contrast/forced-colors behavior, and screen-reader announcements; these gates are not yet certified.
- Keep all existing UI, database/RPC/OIDC integration and API contract checks; update selectors only for intentional glossary/semantic changes.
- Use a separate small commit per plan step. Do not modify retrieval, storage, generation, authorization or deployment behavior as part of visual unification.

## Step 1 completion (historical)

The audit and exact inventories are the only deliverable in this step. No tokens, components, behavior, copy, or application styling have been changed. Plans 2 and 3 have not yet been supplied. **Stop here for owner review before Step 2.**

## Static assets and presentation outside CSS

These values are additional to the CSS totals above. SVG drawing coordinates are artwork/data geometry, not layout spacing tokens.

| Source | Presentation values | Treatment in later steps |
| --- | --- | --- |
| `web/index.html:6` | Browser theme color `#087f6a` | Align browser chrome with the selected palette |
| `web/public/favicon.svg` | Gradient `#075d50` to `#27c7a5`, white `#fff` strokes, corner radius `17`, stroke width `4`, 64-unit viewBox | Keep intentional brand artwork; document its relationship to palette tokens |
| `web/src/AdvancedEvidence.tsx:223` | Evidence-region stroke `#b04416`, stroke width `2` | Use a semantic evidence-highlight color while preserving region geometry |

## Appendix A: exact authored value inventory

Generated from the baseline CSS with PostCSS. Counts are unique declaration strings/literals, not computed browser styles. Location numbers refer to baseline `f6e0211`. Color values inside existing token definitions are included. Spacing shorthands are preserved rather than guessed into a normalized scale.

### font-family (2)

| Value | Source locations |
| --- | --- |
| `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | style.css:4 (:root) |
| `Georgia, serif` | style.css:1074 (.passage-board blockquote); style.css:1474 (.inspector blockquote) |

### Color literals (100)

| Value | Source locations |
| --- | --- |
| `#18221f` | style.css:12; style.css:16 |
| `#f5f7f5` | style.css:13; style.css:39; style.css:45 |
| `#64716c` | style.css:17 |
| `#eff3f0` | style.css:18 |
| `rgba(255, 255, 255, 0.9)` | style.css:19; style.css:323 |
| `#fff` | style.css:20 |
| `#dfe6e1` | style.css:21 |
| `#087f6a` | style.css:22; style.css:226 |
| `#076454` | style.css:23; style.css:27 |
| `#dff7ef` | style.css:24 |
| `#6d5bd0` | style.css:25 |
| `#a64136` | style.css:26 |
| `#064f43` | style.css:28 |
| `rgba(17, 35, 29, 0.05)` | style.css:29 |
| `rgba(32, 59, 49, 0.08)` | style.css:30 |
| `rgba(8, 127, 106, 0.17)` | style.css:31 |
| `rgba(64, 211, 173, 0.14)` | style.css:45 |
| `transparent` | style.css:45; style.css:104; style.css:112; style.css:226; style.css:310; style.css:311; style.css:353; style.css:417; style.css:443; style.css:1154; style.css:1281; style.css:1325 |
| `rgba(109, 91, 208, 0.08)` | style.css:45 |
| `#b8c8c0` | style.css:83; style.css:162 |
| `rgba(25, 53, 43, 0.08)` | style.css:84 |
| `white` | style.css:103; style.css:111; style.css:200; style.css:290; style.css:425; style.css:473; style.css:564 |
| `rgba(8, 127, 106, 0.2)` | style.css:106 |
| `#35423e` | style.css:138 |
| `rgba(255, 255, 255, 0.92)` | style.css:147 |
| `#40534c` | style.css:173 |
| `#efc4bd` | style.css:189 |
| `#802f27` | style.css:191 |
| `#fff2ef` | style.css:192 |
| `#68d8bd` | style.css:226 |
| `#095348` | style.css:226 |
| `#52615c` | style.css:248 |
| `rgba(205, 219, 211, 0.8)` | style.css:266 |
| `rgba(243, 247, 244, 0.83)` | style.css:267 |
| `#10241d` | style.css:278 |
| `#24c6a4` | style.css:291 |
| `rgba(8, 127, 106, 0.25)` | style.css:292 |
| `#7a8782` | style.css:297; style.css:317 |
| `#c3e8dc` | style.css:322 |
| `#075d50` | style.css:324; style.css:424; style.css:754 |
| `rgba(22, 61, 48, 0.08)` | style.css:325 |
| `#53625d` | style.css:355 |
| `#95a19c` | style.css:393 |
| `rgba(255, 255, 255, 0.62)` | style.css:411 |
| `#68736f` | style.css:419 |
| `rgba(24, 54, 43, 0.09)` | style.css:426 |
| `#cae7de` | style.css:441 |
| `rgba(51, 205, 165, 0.17)` | style.css:443 |
| `rgba(255, 255, 255, 0.97)` | style.css:443 |
| `rgba(239, 249, 245, 0.88)` | style.css:443 |
| `#5a6964` | style.css:463 |
| `#927ee8` | style.css:474 |
| `rgba(109, 91, 208, 0.22)` | style.css:475 |
| `#76817d` | style.css:513 |
| `rgba(255, 255, 255, 0.7)` | style.css:524 |
| `#b7c9c0` | style.css:554 |
| `rgba(255, 255, 255, 0.66)` | style.css:556 |
| `#35caaa` | style.css:566 |
| `#43504c` | style.css:629 |
| `#e9eeeb` | style.css:630 |
| `#126146` | style.css:634 |
| `#dff5e9` | style.css:635 |
| `#88392f` | style.css:638 |
| `#fbe7e2` | style.css:639 |
| `rgba(255, 255, 255, 0.72)` | style.css:668 |
| `rgba(255, 255, 255, 0.55)` | style.css:695 |
| `#30b495` | style.css:763 |
| `#fafcfb` | style.css:774 |
| `rgba(11, 38, 29, 0.16)` | style.css:788 |
| `#7a8581` | style.css:835 |
| `rgba(10, 31, 24, 0.2)` | style.css:882 |
| `rgba(0, 0, 0, 0.45)` | style.css:951 |
| `#e7eeea` | style.css:1264; style.css:1266 |
| `#101713` | style.css:1265; style.css:1278; style.css:1281 |
| `#9ca9a3` | style.css:1267 |
| `#18221e` | style.css:1268 |
| `rgba(24, 34, 30, 0.92)` | style.css:1269 |
| `#1b2722` | style.css:1270; style.css:1302 |
| `#304039` | style.css:1271 |
| `#3ad0ad` | style.css:1272 |
| `#0b8e74` | style.css:1273 |
| `#173f35` | style.css:1274 |
| `rgba(41, 160, 130, 0.16)` | style.css:1281 |
| `rgba(16, 23, 19, 0.88)` | style.css:1290 |
| `#2a3933` | style.css:1291 |
| `#eff8f4` | style.css:1294 |
| `#22312b` | style.css:1306 |
| `#53685f` | style.css:1307 |
| `#c7d3ce` | style.css:1310 |
| `#68dfc1` | style.css:1314 |
| `#20322b` | style.css:1315 |
| `rgba(24, 34, 30, 0.72)` | style.css:1321 |
| `#294a40` | style.css:1324 |
| `rgba(38, 173, 137, 0.15)` | style.css:1325 |
| `#18241f` | style.css:1325 |
| `#14201c` | style.css:1325 |
| `#aab7b1` | style.css:1335 |
| `#17211d` | style.css:1338 |
| `#0004` | style.css:1385 |
| `#10251f88` | style.css:1388 |

### line-height (6)

| Value | Source locations |
| --- | --- |
| `1.55` | style.css:15 (:root) |
| `1.12` | style.css:126 (h1, h2, h3) |
| `1.4` | style.css:1059 (.passage-heading h3) |
| `1.75` | style.css:1075 (.passage-board blockquote) |
| `1.7` | style.css:1460 (.excerpt) |
| `1.8` | style.css:1473 (.inspector blockquote) |

### Existing custom properties (25)

| Value | Source locations |
| --- | --- |
| `--ink: #18221f` | style.css:16 (:root) |
| `--muted: #64716c` | style.css:17 (:root) |
| `--subtle: #eff3f0` | style.css:18 (:root) |
| `--surface: rgba(255, 255, 255, 0.9)` | style.css:19 (:root) |
| `--surface-solid: #fff` | style.css:20 (:root) |
| `--line: #dfe6e1` | style.css:21 (:root) |
| `--brand: #087f6a` | style.css:22 (:root) |
| `--brand-dark: #076454` | style.css:23 (:root) |
| `--brand-soft: #dff7ef` | style.css:24 (:root) |
| `--violet: #6d5bd0` | style.css:25 (:root) |
| `--danger: #a64136` | style.css:26 (:root) |
| `--action-background: #076454` | style.css:27 (:root) |
| `--action-hover: #064f43` | style.css:28 (:root) |
| `--shadow-sm: 0 1px 2px rgba(17, 35, 29, 0.05)` | style.css:29 (:root) |
| `--shadow: 0 18px 48px rgba(32, 59, 49, 0.08)` | style.css:30 (:root) |
| `--ring: 0 0 0 4px rgba(8, 127, 106, 0.17)` | style.css:31 (:root) |
| `--ink: #e7eeea` | style.css:1266 (:root) |
| `--muted: #9ca9a3` | style.css:1267 (:root) |
| `--subtle: #18221e` | style.css:1268 (:root) |
| `--surface: rgba(24, 34, 30, 0.92)` | style.css:1269 (:root) |
| `--surface-solid: #1b2722` | style.css:1270 (:root) |
| `--line: #304039` | style.css:1271 (:root) |
| `--brand: #3ad0ad` | style.css:1272 (:root) |
| `--brand-dark: #0b8e74` | style.css:1273 (:root) |
| `--brand-soft: #173f35` | style.css:1274 (:root) |

### Layout and focus declarations (79)

| Value | Source locations |
| --- | --- |
| `min-width: 320px` | style.css:38; style.css:43 |
| `min-height: 100vh` | style.css:44; style.css:209; style.css:259 |
| `min-height: 44px` | style.css:66; style.css:1360 |
| `outline: 2px solid var(--brand)` | style.css:97 |
| `outline-offset: 3px` | style.css:98 |
| `width: 100%` | style.css:145; style.css:309; style.css:365; style.css:671; style.css:805; style.css:810; style.css:824; style.css:907; style.css:957; style.css:1242; style.css:1464; style.css:1522 |
| `outline: none` | style.css:169 |
| `z-index: 100` | style.css:196 |
| `left: 1rem` | style.css:197 |
| `top: -6rem` | style.css:198 |
| `top: 1rem` | style.css:205 |
| `width: min(48vw, 620px)` | style.css:221 |
| `right: -8vw` | style.css:223 |
| `top: 15vh` | style.css:224 |
| `max-width: 850px` | style.css:241 |
| `max-width: 620px` | style.css:247 |
| `grid-template-columns: 288px minmax(0, 1fr)` | style.css:258 |
| `top: 0` | style.css:263 |
| `height: 100vh` | style.css:264; style.css:879 |
| `z-index: 20` | style.css:272 |
| `width: 2.15rem` | style.css:284 |
| `height: 2.15rem` | style.css:285 |
| `min-width: 0` | style.css:364; style.css:663; style.css:1046; style.css:1222; style.css:1525 |
| `max-width: 1500px` | style.css:366 |
| `width: 3px` | style.css:390 |
| `height: 3px` | style.css:391 |
| `width: fit-content` | style.css:406; style.css:752 |
| `max-width: 100%` | style.css:407; style.css:1103 |
| `min-height: 220px` | style.css:435 |
| `grid-template-columns: auto minmax(0, 1fr) auto` | style.css:437 |
| `max-width: 700px` | style.css:462 |
| `width: 3.25rem` | style.css:470 |
| `height: 3.25rem` | style.css:471 |
| `grid-template-columns: repeat(3, minmax(0, 1fr))` | style.css:479 |
| `grid-template-columns: auto 1fr` | style.css:484; style.css:614; style.css:851 |
| `width: 2.35rem` | style.css:494 |
| `height: 2.35rem` | style.css:495 |
| `grid-template-columns: minmax(200px, 0.75fr) 1.5fr` | style.css:519 |
| `grid-template-columns: repeat(3, 1fr)` | style.css:528 |
| `max-width: 780px` | style.css:550 |
| `width: 4rem` | style.css:561 |
| `height: 4rem` | style.css:562 |
| `max-width: 430px` | style.css:569 |
| `grid-template-columns: auto minmax(220px, 1fr) auto` | style.css:596 |
| `grid-template-columns: auto minmax(150px, 0.65fr) auto minmax(150px, 0.65fr) auto` | style.css:650 |
| `grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))` | style.css:658 |
| `z-index: 50` | style.css:784 |
| `inset: 1rem 1rem 1rem auto` | style.css:785 |
| `width: min(520px, calc(100vw - 2rem))` | style.css:786 |
| `inset: 0` | style.css:809 |
| `height: 100%` | style.css:811; style.css:958 |
| `max-height: 24rem` | style.css:815 |
| `grid-template-columns: 240px minmax(0, 1fr)` | style.css:848 |
| `grid-template-columns: 1fr` | style.css:858; style.css:861; style.css:913; style.css:922; style.css:926; style.css:935 |
| `grid-template-columns: 1fr 1fr` | style.css:864 |
| `inset: 0 auto 0 0` | style.css:877 |
| `width: min(88vw, 320px)` | style.css:878 |
| `max-width: 110px` | style.css:904 |
| `width: min(88vw, 340px)` | style.css:943 |
| `max-width: 100vw` | style.css:944 |
| `height: 100dvh` | style.css:945 |
| `max-height: 100dvh` | style.css:946 |
| `max-width: 60ch` | style.css:978 |
| `max-width: 65ch` | style.css:1028 |
| `grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr))` | style.css:1042 |
| `min-width: 44px` | style.css:1065 |
| `max-height: 22rem` | style.css:1077 |
| `max-width: 420px` | style.css:1175 |
| `outline: 3px solid var(--brand)` | style.css:1180 |
| `width: min(620px, calc(100vw - 2rem))` | style.css:1379 |
| `max-height: 76vh` | style.css:1380 |
| `width: 44px` | style.css:1405 |
| `height: 44px` | style.css:1406 |
| `max-height: 42vh` | style.css:1415 |
| `min-height: 56px` | style.css:1423 |
| `max-width: 75ch` | style.css:1461; style.css:1472 |
| `height: 60vh` | style.css:1465 |
| `max-height: 20rem` | style.css:1487 |
| `grid-template-columns: repeat(2, minmax(0, 1fr))` | style.css:1521 |

### Spacing declarations (105)

| Value | Source locations |
| --- | --- |
| `margin: 0` | style.css:42; style.css:382; style.css:512; style.css:531; style.css:940; style.css:1060; style.css:1090; style.css:1192; style.css:1402; style.css:1448 |
| `padding: 0.62rem 0.9rem` | style.css:71 |
| `gap: 0.45rem` | style.css:79 |
| `margin-top: 0` | style.css:120 |
| `padding: 0.76rem 0.85rem` | style.css:150 |
| `margin: 0 0 0.65rem` | style.css:177 |
| `padding: 0.85rem 1rem` | style.css:188 |
| `padding: 0.7rem 1rem` | style.css:199 |
| `padding: 8vh max(6vw, 2rem)` | style.css:214 |
| `margin-bottom: clamp(4rem, 10vh, 8rem)` | style.css:238 |
| `margin-bottom: 1.5rem` | style.css:244; style.css:968 |
| `margin-bottom: 2.2rem` | style.css:250 |
| `margin-top: 1.5rem` | style.css:253; style.css:1189 |
| `padding: 1.45rem 1.2rem` | style.css:265 |
| `gap: 1.35rem` | style.css:271 |
| `gap: 0.62rem` | style.css:277 |
| `margin-bottom: -0.75rem` | style.css:295 |
| `padding-left: 0.2rem` | style.css:296 |
| `gap: 0.35rem` | style.css:301; style.css:403; style.css:1126; style.css:1418 |
| `padding: 0.72rem 0.8rem` | style.css:312 |
| `margin-top: 0.12rem` | style.css:319 |
| `gap: 0.55rem` | style.css:329 |
| `padding-top: 0.25rem` | style.css:330 |
| `margin-top: auto` | style.css:336 |
| `gap: 0.6rem` | style.css:338 |
| `padding-top: 1rem` | style.css:339; style.css:834 |
| `gap: 0.4rem` | style.css:345; style.css:385; style.css:1202 |
| `padding: 0.45rem 0` | style.css:351 |
| `margin: 0 auto` | style.css:367; style.css:570 |
| `padding: 2.2rem clamp(1.2rem, 4vw, 4.5rem) 3rem` | style.css:368 |
| `gap: 2rem` | style.css:374; style.css:520 |
| `padding-bottom: 1.6rem` | style.css:375 |
| `margin-bottom: 0.55rem` | style.css:378; style.css:975 |
| `margin-inline: 0.25rem` | style.css:394 |
| `padding: 0.35rem` | style.css:404 |
| `margin-bottom: 2rem` | style.css:405; style.css:1351 |
| `padding: 0.55rem 0.82rem` | style.css:421 |
| `gap: 1.2rem` | style.css:431; style.css:439 |
| `padding: clamp(1.5rem, 4vw, 2.7rem)` | style.css:440 |
| `margin-bottom: 0.7rem` | style.css:459 |
| `margin-bottom: 0` | style.css:464; style.css:980 |
| `gap: 1rem` | style.css:480; style.css:659; style.css:967; style.css:1024; style.css:1043; style.css:1115; style.css:1188; style.css:1350; style.css:1398; style.css:1444 |
| `gap: 0.2rem 0.75rem` | style.css:485 |
| `padding: 1.25rem` | style.css:486; style.css:645; style.css:704; style.css:748 |
| `padding: 1.5rem` | style.css:521 |
| `gap: 0.75rem` | style.css:529; style.css:597; style.css:901 |
| `padding: 0` | style.css:532; style.css:610; style.css:941; style.css:1153; style.css:1206; style.css:1378; style.css:1480 |
| `gap: 0.7rem` | style.css:536; style.css:644; style.css:726; style.css:1411 |
| `margin: 0.25rem 0 0` | style.css:546 |
| `margin: 4rem auto` | style.css:551 |
| `padding: 4rem 2rem` | style.css:552 |
| `margin: 0 auto 1.25rem` | style.css:563 |
| `padding: 1.35rem` | style.css:587 |
| `padding: 1rem` | style.css:599; style.css:664; style.css:714; style.css:727; style.css:770; style.css:997; style.css:1050; style.css:1116 |
| `gap: 0.5rem` | style.css:609; style.css:682; style.css:737; style.css:1056; style.css:1096; style.css:1371 |
| `gap: 0.25rem 0.8rem` | style.css:615 |
| `padding: 0.8rem 0` | style.css:616 |
| `padding: 0.18rem 0.5rem` | style.css:627 |
| `margin-bottom: 1rem` | style.css:646; style.css:1025; style.css:1511 |
| `gap: 0.65rem` | style.css:654 |
| `margin-top: 0.55rem` | style.css:674 |
| `padding: 0.8rem` | style.css:675 |
| `margin: 0.4rem 0 0` | style.css:686 |
| `margin-block: 1rem` | style.css:691; style.css:728; style.css:738; style.css:799 |
| `padding: 0.75rem 1rem` | style.css:692 |
| `margin-top: 1rem` | style.css:705; style.css:1038; style.css:1467 |
| `padding-right: 8rem` | style.css:708 |
| `margin-top: 0.75rem` | style.css:711 |
| `padding: clamp(1.2rem, 3vw, 2rem)` | style.css:721 |
| `margin-block: 1.2rem` | style.css:747; style.css:761 |
| `padding: 0.2rem 0.55rem` | style.css:753 |
| `padding-left: 1rem` | style.css:762; style.css:792 |
| `margin: 0.2rem` | style.css:766 |
| `margin-block: 0.8rem` | style.css:771 |
| `margin: 0 0 0.7rem` | style.css:780 |
| `margin-inline: 0` | style.css:791 |
| `padding: 0.5rem` | style.css:829; style.css:1064 |
| `margin-top: 3rem` | style.css:833 |
| `margin-left: auto` | style.css:889 |
| `padding: 0.4rem` | style.css:890 |
| `margin-bottom: 0.8rem` | style.css:894 |
| `padding: 0.48rem` | style.css:895 |
| `padding: 1.2rem 1rem 2rem` | style.css:898 |
| `margin-top: 1.6rem` | style.css:972 |
| `margin-bottom: 0.6rem` | style.css:986 |
| `margin: 1rem 0` | style.css:990; style.css:1076; style.css:1119; style.css:1412; style.css:1445 |
| `margin-right: 0.5rem` | style.css:1005 |
| `margin-left: 0.6rem` | style.css:1010 |
| `padding: 0.1rem 0.5rem` | style.css:1011 |
| `padding: 0 1rem 1rem` | style.css:1018; style.css:1097 |
| `margin-top: 0.5rem` | style.css:1071 |
| `margin-top: 0.6rem` | style.css:1086 |
| `margin: 0.35rem 0 0.75rem` | style.css:1142 |
| `padding: 0.4rem 0.7rem` | style.css:1143 |
| `padding: 2rem 1rem` | style.css:1160 |
| `margin: 0 auto 0.85rem` | style.css:1164 |
| `margin-bottom: 0.5rem` | style.css:1168 |
| `margin: 0.5rem auto 0` | style.css:1177 |
| `margin: 0.8rem 0 0` | style.css:1207 |
| `gap: 0.8rem` | style.css:1212 |
| `padding: 0.75rem 0` | style.css:1214 |
| `padding: 0.12rem 0.35rem` | style.css:1363 |
| `margin: 12vh auto auto` | style.css:1377 |
| `padding: 1.2rem` | style.css:1392 |
| `margin: 1rem 0 0` | style.css:1436 |

### border-radius (16)

| Value | Source locations |
| --- | --- |
| `0.72rem` | style.css:68 (button, .button); style.css:149 (input, select, textarea); style.css:289 (.logo-mark) |
| `0.8rem` | style.css:190 (.error); style.css:773 (.comparison); style.css:1118 (.evidence-controls) |
| `0.6rem` | style.css:202 (.skip); style.css:1049 (.passage-board article) |
| `50%` | style.css:225 (.welcome::after); style.css:392 (.header-meta span) |
| `0.9rem` | style.css:410 (.view-tabs) |
| `1.3rem` | style.css:442 (.hero-card) |
| `1rem` | style.css:472 (.hero-icon); style.css:488 (.stat-grid article); style.css:523 (.workflow-card); style.css:582 (.uploads, .search-form, .saved-research, .answer, .inspector, .citation-inspector, .consent); style.css:1013 (.count-pill); style.css:1158 (.upload-dropzone); style.css:1382 (.command-dialog) |
| `0.75rem` | style.css:499 (.stat-grid article > span); style.css:694 (.diagnostics); style.css:716 (.no-results) |
| `1.2rem` | style.css:555 (.empty) |
| `1.25rem` | style.css:565 (.empty-symbol) |
| `0.85rem` | style.css:600 (.uploads form); style.css:729 (.saved-research > form); style.css:992 (.evidence-tray, .recent-searches) |
| `999px` | style.css:628 (.status); style.css:755 (.answer-status) |
| `0.95rem` | style.css:667 (.ranking) |
| `0.7rem` | style.css:801 (.advanced-page) |
| `0.3rem` | style.css:1365 (kbd) |
| `0.5rem` | style.css:1468 (.inspector iframe) |

### box-shadow (13)

| Value | Source locations |
| --- | --- |
| `var(--shadow-sm)` | style.css:73 (button, .button); style.css:151 (input, select, textarea); style.css:412 (.view-tabs); style.css:490 (.stat-grid article); style.css:584 (.uploads, .search-form, .saved-research, .answer, .inspector, .citation-inspector, .consent) |
| `0 7px 18px rgba(25, 53, 43, 0.08)` | style.css:84 (button:hover, .button:hover) |
| `var(--ring)` | style.css:99 (button:focus-visible, a:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible, summary:focus-visible); style.css:168 (input:focus, select:focus, textarea:focus) |
| `0 10px 25px rgba(8, 127, 106, 0.2)` | style.css:106 (.primary, a.primary) |
| `0 9px 20px rgba(8, 127, 106, 0.25)` | style.css:292 (.logo-mark) |
| `none` | style.css:313 (.collection); style.css:354 (.account button); style.css:418 (.view-tabs button); style.css:676 (.hit); style.css:1144 (.shortlist-action); style.css:1424 (.command-result); style.css:1492 (.hero-card); style.css:1497 (.hero-icon) |
| `0 8px 25px rgba(22, 61, 48, 0.08)` | style.css:325 (.collection.selected) |
| `0 4px 14px rgba(24, 54, 43, 0.09)` | style.css:426 (.view-tabs button.active) |
| `var(--shadow)` | style.css:454 (.hero-card) |
| `0 12px 24px rgba(109, 91, 208, 0.22)` | style.css:475 (.hero-icon) |
| `-18px 0 55px rgba(11, 38, 29, 0.16)` | style.css:788 (.citation-inspector) |
| `20px 0 60px rgba(10, 31, 24, 0.2)` | style.css:882 (.navigation) |
| `0 24px 80px #0004` | style.css:1385 (.command-dialog) |

### transition (3)

| Value | Source locations |
| --- | --- |
| `0.16s ease` | style.css:74 (button, .button) |
| `border-color 0.16s, box-shadow 0.16s` | style.css:152 (input, select, textarea) |
| `transform 0.22s ease` | style.css:881 (.navigation) |

### font-weight (4)

| Value | Source locations |
| --- | --- |
| `600` | style.css:999 (.evidence-tray > summary, .recent-searches > summary); style.css:1227 (.upload-queue strong) |
| `650` | style.css:107 (.primary, a.primary); style.css:140 (label); style.css:985 (.section-kicker) |
| `700` | style.css:683 (.hit-title); style.css:700 (summary); style.css:777 (.saved-research dt) |
| `800` | style.css:180 (.eyebrow); style.css:280 (.wordmark); style.css:541 (.workflow-card li > span) |

### letter-spacing (6)

| Value | Source locations |
| --- | --- |
| `-0.035em` | style.css:125 (h1, h2, h3) |
| `0.15em` | style.css:181 (.eyebrow) |
| `-0.065em` | style.css:243 (.welcome h1) |
| `-0.04em` | style.css:281 (.wordmark) |
| `0.08em` | style.css:506 (.stat-grid small) |
| `0.03em` | style.css:1505 (.eyebrow) |

### font-size (24)

| Value | Source locations |
| --- | --- |
| `clamp(2rem, 4vw, 3.3rem)` | style.css:129 (h1) |
| `clamp(1.35rem, 2vw, 1.75rem)` | style.css:132 (h2) |
| `1.08rem` | style.css:135 (h3); style.css:509 (.stat-grid strong) |
| `0.83rem` | style.css:139 (label); style.css:592 (.uploads > div:first-child p) |
| `0.82em` | style.css:172 (code) |
| `0.67rem` | style.css:179 (.eyebrow) |
| `0.86rem` | style.css:185 (.muted) |
| `clamp(3.4rem, 7vw, 6.8rem)` | style.css:242 (.welcome h1) |
| `1.15rem` | style.css:249 (.intro) |
| `1.23rem` | style.css:279 (.wordmark) |
| `0.68rem` | style.css:318 (.collection small); style.css:837 (footer); style.css:1366 (kbd) |
| `0.82rem` | style.css:333 (.new-collection button); style.css:699 (summary) |
| `0.72rem` | style.css:347 (.account span); style.css:757 (.answer-status) |
| `0.76rem` | style.css:356 (.account button); style.css:387 (.header-meta) |
| `0.75rem` | style.css:399 (.quiet); style.css:514 (.stat-grid p); style.css:545 (.workflow-card li p); style.css:1429 (.command-result small); style.css:1437 (.command-help) |
| `0.8rem` | style.css:420 (.view-tabs button); style.css:618 (.jobs li); style.css:767 (.citation); style.css:984 (.section-kicker); style.css:1015 (.count-pill); style.css:1070 (.passage-meta); style.css:1083 (.passage-board details); style.css:1196 (.queue-heading > span, .upload-actions > span); style.css:1353 (.workspace-toolbar); style.css:1359 (.command-trigger); style.css:1374 (.collection-filter input) |
| `clamp(1.7rem, 3vw, 2.45rem)` | style.css:458 (.hero-card h2) |
| `0.69rem` | style.css:504 (.stat-grid small) |
| `0.7rem` | style.css:540 (.workflow-card li > span) |
| `0.78rem` | style.css:688 (.excerpt); style.css:1141 (.shortlist-action) |
| `0.85rem` | style.css:1029 (.tray-intro p); style.css:1138 (.interaction-notice); style.css:1172 (.upload-dropzone p); style.css:1450 (.result-toolbar p) |
| `0.9rem` | style.css:1228 (.upload-queue strong) |
| `1.2rem` | style.css:1401 (.command-heading h2) |
| `1.05rem` | style.css:1475 (.inspector blockquote) |

### animation (2)

| Value | Source locations |
| --- | --- |
| `rise 0.28s ease-out` | style.css:432 (.dashboard); style.css:588 (.uploads); style.css:722 (.saved-research) |
| `none` | style.css:1502 (.dashboard, .uploads, .saved-research) |

### text-transform (3)

| Value | Source locations |
| --- | --- |
| `uppercase` | style.css:505 (.stat-grid small) |
| `capitalize` | style.css:631 (.status); style.css:758 (.answer-status); style.css:1356 (.workspace-toolbar > span) |
| `none` | style.css:1506 (.eyebrow) |

### scroll-behavior (1)

| Value | Source locations |
| --- | --- |
| `auto` | style.css:1256 (*,   *::before,   *::after) |

### transition-duration (1)

| Value | Source locations |
| --- | --- |
| `0.01ms` | style.css:1257 (*,   *::before,   *::after) |

### animation-duration (1)

| Value | Source locations |
| --- | --- |
| `0.01ms` | style.css:1258 (*,   *::before,   *::after) |

### CSS conditions and keyframes (6)

| Value | Source locations |
| --- | --- |
| `@import "tailwindcss"` | style.css:1 |
| `@keyframes rise` | style.css:839 |
| `@media (max-width: 980px)` | style.css:846 |
| `@media (max-width: 720px)` | style.css:871; style.css:1236; style.css:1508 |
| `@media (prefers-reduced-motion: reduce)` | style.css:1252 |
| `@media (prefers-color-scheme: dark)` | style.css:1262 |

### Icon imports (5)

| Value | Source locations |
| --- | --- |
| `Command, Search, X` | CommandMenu.tsx:2 |
| `Download, BookmarkCheck, X` | EvidenceTray.tsx:1 |
| `Archive, ArrowUpRight, BookOpenText, Database, FileText, LayoutDashboard, LogOut, Menu, MessageSquareText, Plus, Search as SearchIcon, ShieldCheck, Sparkles, X` | main.tsx:11 |
| `BookmarkPlus, BookmarkCheck, SlidersHorizontal, History, Search as SearchIcon, X` | Search.tsx:3 |
| `FileText, UploadCloud, X, CheckCircle2` | Uploads.tsx:3 |

## Appendix B: interactive and structural JSX sites

Every authored button, link, field, dialog, aside, disclosure, table, image, and SVG opening site is listed below. Mapped elements can create multiple runtime instances. Attributes are retained as source expressions; no private runtime data was captured. Classless controls inherit the global element styles.

| Element | Source | Attributes |
| --- | --- | --- |
| table | AdvancedEvidence.tsx:110 | `` |
| img | AdvancedEvidence.tsx:207 | `src={'${path}/images/page'} alt={'Retained source page ${value.locator.page}'}` |
| svg | AdvancedEvidence.tsx:211 | `viewBox={'0 0 ${width} ${height}'} preserveAspectRatio="none" role="img" aria-label="Highlighted evidence region"` |
| a | AdvancedEvidence.tsx:228 | `href={'${path}/original#page=${value.locator.page}'} target="_blank" rel="noreferrer"` |
| summary | AdvancedEvidence.tsx:244 | `` |
| details | AdvancedEvidence.tsx:243 | `` |
| button | CommandMenu.tsx:55 | `className="command-trigger" onClick={open}` |
| button | CommandMenu.tsx:71 | `aria-label="Close quick actions" onClick={() => dialog.current?.close()}` |
| input | CommandMenu.tsx:80 | `autoFocus ref={input} role="combobox" aria-expanded={opened} aria-autocomplete="list" aria-controls={listId} aria-activedescendant={ activeIndex >= 0 ? '${listId}-${activeIndex}' : undefined } aria-label="Find actions and collections" placeholder="Search actions or collections…" value={query} onChange={(event) => { setQuery(event.target.value); setSelected(0); }} onKeyDown={(event) => { if (event.key === "ArrowDown" \|\| event.key === "ArrowUp") { event.preventDefault(); setSelected((index) => Math.max( 0, Math.min( matches.length - 1, index + (event.key === "ArrowDown" ? 1 : -1), ), ), ); } if (event.key === "Home" \|\| event.key === "End") { event.preventDefault(); setSelected( event.key === "Home" ? 0 : Math.max(0, matches.length - 1), ); } if (event.key === "Enter" && matches[activeIndex]) { event.preventDefault(); choose(matches[activeIndex]); } }}` |
| button | CommandMenu.tsx:130 | `key={action.id} id={'${listId}-${index}'} role="option" aria-selected={activeIndex === index} tabIndex={-1} className={ activeIndex === index ? "command-result selected" : "command-result" } onClick={() => choose(action)} onMouseMove={() => setSelected(index)}` |
| dialog | CommandMenu.tsx:59 | `ref={dialog} className="command-dialog" aria-labelledby="command-title" onClose={() => setOpened(false)} onClick={(event) => { if (event.target === event.currentTarget) dialog.current?.close(); }}` |
| summary | EvidenceTray.tsx:50 | `` |
| button | EvidenceTray.tsx:61 | `onClick={download} disabled={!items.length}` |
| button | EvidenceTray.tsx:76 | `aria-label={'Remove ${item.hit.title} from shortlist'} onClick={() => remove(passageKey(item))}` |
| summary | EvidenceTray.tsx:93 | `` |
| details | EvidenceTray.tsx:92 | `` |
| details | EvidenceTray.tsx:49 | `className="evidence-tray"` |
| a | main.tsx:117 | `className="button primary" href="/auth/login"` |
| a | main.tsx:132 | `className="skip" href="#research"` |
| button | main.tsx:144 | `className="mobile-close" aria-label="Close navigation" onClick={() => setNavigationOpen(false)}` |
| input | main.tsx:155 | `type="search" value={collectionFilter} onChange={(event) => setCollectionFilter(event.target.value)} placeholder="Filter collections…"` |
| button | main.tsx:168 | `key={item.collection_id} className={ selected === item.collection_id ? "collection selected" : "collection" } aria-pressed={selected === item.collection_id} onClick={() => { setSelected(item.collection_id); setError(""); setView("overview"); setNavigationOpen(false); }}` |
| input | main.tsx:200 | `id="collection-title" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={120} required placeholder="e.g. Retrieval methods"` |
| button | main.tsx:208 | `disabled={busy \|\| !title.trim()} type="submit"` |
| button | main.tsx:216 | `onClick={logout}` |
| button | main.tsx:264 | `className="mobile-menu" aria-label="Open navigation" aria-controls="workspace-navigation" aria-expanded={navigationOpen} onClick={() => setNavigationOpen(true)}` |
| button | main.tsx:287 | `className="quiet" onClick={archive} disabled={busy}` |
| button | main.tsx:307 | `key={id} className={view === id ? "active" : ""} aria-current={view === id ? "page" : undefined} onClick={() => setView(id)}` |
| button | main.tsx:336 | `className="primary" onClick={() => setView(active.active_snapshot ? "search" : "sources") }` |
| aside | NavigationPanel.tsx:37 | `id="workspace-navigation" className="navigation"` |
| aside | NavigationPanel.tsx:69 | `className="navigation"` |
| dialog | NavigationPanel.tsx:42 | `id="workspace-navigation" ref={dialog} className="navigation-dialog" aria-label="Collection navigation" onClose={onClose} onKeyDown={(event) => { if (event.key !== "Tab") return; const targets = Array.from( event.currentTarget.querySelectorAll<HTMLElement>( 'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]', ), ).filter((element) => element.getClientRects().length > 0); const first = targets[0], last = targets[targets.length - 1]; if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); } }} onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}` |
| button | Research.tsx:332 | `className="quiet citation" key={id} onClick={(event) => inspect(item, event.currentTarget)} aria-label={'Inspect citation ${id}'}` |
| select | Research.tsx:351 | `id="conversation" disabled={busy} value={conversation} onChange={(event) => { inspectionVersion.current += 1; setConversation(event.target.value); setRun(null); setSelectedRunId(null); setRunConnection("connected"); setEvidence(null); setRequestKey(crypto.randomUUID()); }}` |
| textarea | Research.tsx:379 | `id="research-question" disabled={busy} value={question} maxLength={4096} required rows={3} onChange={(event) => { setQuestion(event.target.value); setRequestKey(crypto.randomUUID()); }}` |
| input | Research.tsx:394 | `id="effective-query" disabled={busy} value={effective} maxLength={4096} onChange={(event) => { setEffective(event.target.value); setRequestKey(crypto.randomUUID()); }} placeholder="Include the method or paper your follow-up refers to"` |
| select | Research.tsx:406 | `id="generation-provider" disabled={busy} value={provider} onChange={(event) => { setProvider(event.target.value); setRequestKey(crypto.randomUUID()); }}` |
| button | Research.tsx:424 | `className="primary" disabled={ busy \|\| !question.trim() \|\| !collection.active_snapshot \|\| !selectedProvider?.consented }` |
| button | Research.tsx:453 | `onClick={() => consent(!selectedProvider.consented)}` |
| button | Research.tsx:466 | `key={item.run_id} disabled={busy} aria-pressed={selectedRunId === item.run_id} onClick={() => { inspectionVersion.current += 1; // Reauthorize history before showing a cached answer or enabling exports. setRun(null); setSelectedRunId(item.run_id); setRunRefresh((value) => value + 1); setRunConnection("retrying"); setEvidence(null); }}` |
| button | Research.tsx:493 | `type="button" onClick={() => { setRunConnection("retrying"); setRunRefresh((value) => value + 1); }}` |
| button | Research.tsx:510 | `disabled={busy} onClick={async () => { try { await api( '/api/v1/runs/${run.run_id}/cancel', { method: "POST" }, session.csrf_token, ); } catch (error) { fail(error); } }}` |
| button | Research.tsx:578 | `key={format} onClick={() => exportRun(format)}` |
| button | Research.tsx:587 | `disabled={busy} onClick={() => submit("historical", true)}` |
| button | Research.tsx:593 | `disabled={busy} onClick={() => submit("current", true)}` |
| summary | Research.tsx:599 | `` |
| details | Research.tsx:598 | `` |
| button | Research.tsx:622 | `ref={citationClose} onClick={closeCitation}` |
| a | Research.tsx:640 | `target="_blank" rel="noreferrer" href={'/api/v1/sources/${evidence.source_id}?snapshot_id=${evidence.snapshot_id}#page=${evidence.page_range?.[0] ?? 1}'}` |
| aside | Research.tsx:612 | `className="citation-inspector" aria-label="Citation evidence" onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); closeCitation(); } }}` |
| textarea | Search.tsx:157 | `id="question" rows={2} maxLength={4096} required value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if ( (event.ctrlKey \|\| event.metaKey) && event.key === "Enter" && !busy && collection.active_snapshot ) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="How does dense retrieval compare with lexical matching?"` |
| select | Search.tsx:179 | `id="parser" value={mode} onChange={(event) => { setMode(event.target.value); if (event.target.value === "structured") setRetrieval("sparse"); }}` |
| select | Search.tsx:191 | `id="retrieval" value={retrieval} onChange={(event) => setRetrieval(event.target.value)}` |
| button | Search.tsx:207 | `type="submit" className="primary" disabled={busy \|\| !collection.active_snapshot}` |
| button | Search.tsx:215 | `type="button" onClick={() => { request.current?.abort(); setBusy(false); setNotice( "Search cancelled. Previous results are still available.", ); }}` |
| summary | Search.tsx:237 | `` |
| button | Search.tsx:243 | `key={'${item.query}-${index}'} onClick={() => { setQuery(item.query); setMode(item.mode); setRetrieval(item.retrieval); document.getElementById("question")?.focus(); }}` |
| details | Search.tsx:236 | `className="recent-searches"` |
| button | Search.tsx:299 | `type="button" aria-pressed={compact} onClick={() => setCompact((value) => !value)}` |
| input | Search.tsx:311 | `type="search" value={filter} placeholder="Find a title or phrase…" onChange={(event) => setFilter(event.target.value)}` |
| select | Search.tsx:320 | `value={method} onChange={(event) => setMethod(event.target.value)}` |
| summary | Search.tsx:337 | `` |
| details | Search.tsx:336 | `className="diagnostics"` |
| button | Search.tsx:404 | `className={ selected?.chunk_id === hit.chunk_id ? "hit active" : "hit" } onClick={(event) => inspect(hit, event.currentTarget) }` |
| button | Search.tsx:428 | `className="shortlist-action" aria-pressed={shortlist.some( (item) => item.snapshot_id === result.snapshot_id && item.hit.chunk_id === hit.chunk_id, )} onClick={() => save(hit)}` |
| button | Search.tsx:469 | `aria-label="Close evidence inspector" onClick={closeInspector}` |
| a | Search.tsx:492 | `className="button source-link" target="_blank" rel="noreferrer" href={'${sourceURL}#page=${selected.page_range?.[0] ?? 1}'}` |
| aside | Search.tsx:455 | `ref={inspector} tabIndex={-1} className="inspector" aria-label="Evidence inspector" onKeyDown={(event) => { if (event.key === "Escape") { event.stopPropagation(); closeInspector(); } }}` |
| input | Uploads.tsx:184 | `id="documents" ref={input} type="file" accept=".pdf,.txt,.md" multiple disabled={sending \|\| pending} onChange={(event) => { addFiles(Array.from(event.target.files ?? [])); event.target.value = ""; }}` |
| button | Uploads.tsx:216 | `type="button" disabled={sending} aria-label={'Remove ${file.name}'} onClick={() => { setFiles((current) => current.filter((_, position) => position !== index), ); requestKey.current = crypto.randomUUID(); }}` |
| button | Uploads.tsx:239 | `className="primary" type="submit" disabled={ sending \|\| pending \|\| !files.length \|\| files.some((file) => Boolean(fileProblem(file))) }` |
| summary | Uploads.tsx:262 | `` |
| details | Uploads.tsx:261 | `open` |

## Appendix C: icon usage sites

The entries are JSX components with explicit size attributes; these are Lucide icons in the reviewed source. Dynamic view-navigation icons are included as `Icon`. The separate evidence-region SVG is data visualization, not a competing icon library.

| Icon | Source | Attributes |
| --- | --- | --- |
| Command | CommandMenu.tsx:56 | `size={16}` |
| X | CommandMenu.tsx:75 | `size={18}` |
| Search | CommandMenu.tsx:79 | `size={18}` |
| BookmarkCheck | EvidenceTray.tsx:51 | `size={18} aria-hidden="true"` |
| Download | EvidenceTray.tsx:62 | `size={16} aria-hidden="true"` |
| X | EvidenceTray.tsx:80 | `size={16}` |
| BookOpenText | main.tsx:103 | `size={19}` |
| ArrowUpRight | main.tsx:118 | `size={17}` |
| BookOpenText | main.tsx:141 | `size={18}` |
| X | main.tsx:149 | `size={18}` |
| Plus | main.tsx:209 | `size={16}` |
| ShieldCheck | main.tsx:214 | `size={14}` |
| LogOut | main.tsx:217 | `size={14}` |
| Menu | main.tsx:271 | `size={19}` |
| ShieldCheck | main.tsx:277 | `size={14}` |
| Archive | main.tsx:288 | `size={15}` |
| Icon | main.tsx:313 | `size={16}` |
| Sparkles | main.tsx:323 | `size={24}` |
| ArrowUpRight | main.tsx:345 | `size={16}` |
| Database | main.tsx:351 | `size={18}` |
| SearchIcon | main.tsx:365 | `size={18}` |
| ShieldCheck | main.tsx:373 | `size={18}` |
| Sparkles | main.tsx:437 | `size={30}` |
| SearchIcon | Search.tsx:153 | `size={28} aria-hidden="true"` |
| History | Search.tsx:238 | `size={16} aria-hidden="true"` |
| SlidersHorizontal | Search.tsx:308 | `size={18} aria-hidden="true"` |
| BookmarkPlus | Search.tsx:444 | `size={15} aria-hidden="true"` |
| BookmarkCheck | Search.tsx:442 | `size={15} aria-hidden="true"` |
| X | Search.tsx:473 | `size={18}` |
| UploadCloud | Uploads.tsx:178 | `size={32} aria-hidden="true"` |
| FileText | Uploads.tsx:209 | `size={19} aria-hidden="true"` |
| X | Uploads.tsx:227 | `size={17}` |
| CheckCircle2 | Uploads.tsx:236 | `size={16} aria-hidden="true"` |
