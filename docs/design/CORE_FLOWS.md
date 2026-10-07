# RetrieVec core flows and navigation

The 2026-10-06 [material refinement](MATERIALS.md) changes presentation only:
collection-header and navigation modules retain the same actions and activation
counts. All three destination controls remain visible at 320px with doubled text;
the 33-test browser run preserved shortcuts, focus return, Escape, scoped lookup,
upload retry keys, consent and provenance.

Date: 2026-09-29. **Navigation and implementation approved by the owner.** This document preserves the original flow inventory and proposal. The 2026-10-04 UI-unification phase builds on the navigation already merged into `main`; see [current audit status](AUDIT.md#implementation-update--2026-10-04) and [shared component contracts](../DESIGN_SYSTEM.md).

Current presentation uses Ask → Answer / Find passages, Sources, and Saved research. Answer composition is headed **Cited answers**. Collection details/readiness replace the old overview, and archive uses the existing Undo flow. UI unification retains the existing shortcuts, focus/Escape behavior, retry keys, session cleanup, consent rules, and research state machine; Phase 2 completes consent-aware initial mode selection, contextual quick actions, More disclosures, and shared evidence context. Retrieval defaults are unchanged. The audit lists actual automated coverage and remaining manual/integration gates.

## One mental model

A collection holds sources. Ask questions of that collection, then verify each answer against its retained evidence. Saved research preserves the question, answer, model configuration, and source snapshot.

The three core jobs are:

1. **Add sources:** create/select a collection, add documents, understand when they are searchable.
2. **Ask questions:** get a cited answer or search passages directly, without configuring a retrieval experiment first.
3. **Verify evidence:** inspect the exact retained passage and its original source, assess limitations, and return to the answer without losing context.

These are inferred from the implemented product and the brief, not user-research findings.

## Current feature map and click counts

Updated 2026-10-04 for phase 2. Start in a signed-in collection; prerequisites are listed below. Count actual navigation, disclosure and action activations, excluding typing, scrolling, waiting and OS file-picker interaction. A native select takes two activations (open, choose). A quick action takes two (open palette, choose match); its target receives focus and enclosing disclosures open. Activating an export, replay or comparison is a separate third action. Keyboard equivalents do not require mouse clicks.

The desktop and mobile quick-action paths are exercised by web/ui-tests/phase2.spec.ts, with a JSON attachment recording the two executed activations for each target. Existing interaction tests exercise source upload, shortlist/export, collection switching, archive/Undo, dialogs and keyboard behavior. Direct-path counts below count the current controls; they are not timing measurements or usability-study results. A path longer than three retains a discoverable quick-action alternative instead of hiding its extra steps.

| Feature | Current path | Activations | Prerequisite / alternative |
| --- | --- | ---: | --- |
| Sign in / out | Welcome → Sign in; sidebar → Sign out | 1 | Identity-provider steps excluded; mobile sign out adds navigation open |
| Switch / filter collections | Collection button / filter field | 1 | Mobile adds navigation open; collection matches also in quick actions |
| Create collection | Title field → Create | 2 | Mobile 3; returns to Ask |
| Archive / restore | Archive collection / Undo | 1 each | Owner; Undo does not restart cancelled work |
| Readiness and access | Collection header | 0 | Visible context, no Overview destination |
| Snapshot details | Sources → Collection details | 2 | Disclosure under header |
| Three destinations | Ask / Sources / Saved research | 1 | Tabs stay visible on mobile; quick-action equivalent 2 |
| Choose question mode | Answer / Find passages | 1 | In Ask; Answer defaults only with a configured, consented provider |
| Add sources | Sources → Choose documents | 2 | Quick action focuses file input in 2; activate picker adds 1 |
| Submit / retry upload | Sources → Upload documents | 2 | Files already selected; unchanged retry batch keeps its key |
| Remove queued file | Sources → Remove file | 2 | Local queue only |
| Validation, stages and automatic retries | Sources | 1 | Current source/processing state exists |
| Focus composer | Quick actions → Focus question composer | 2 | Chooses current Ask mode; does not submit |
| Search / generate | Ask → mode if needed → submit | 2–3 | Question entered; snapshot; generation also needs consented provider |
| Keyboard submission | Cmd/Ctrl+Enter | 1 shortcut | Both modes; disabled readiness/consent and IME composition respected |
| Compare methods | Quick actions → Compare retrieval methods → Compare methods | 3 | Prepares comparison; submit separately when question ready |
| Boolean syntax / retrieval selector | Ask passage mode → More search options → select | 3 within mode | Native select counts 2; mode/destination adds steps. Indexed in quick actions |
| Restore recent query | Quick actions → Restore a recent query → query | 3 | Restores fields; does not submit |
| Compact/full excerpts | Compact results | 1 within mode | Results exist |
| Text filter | Quick actions → Filter returned passages | 2 | Results exist; local filter, no retrieval request |
| Returned method filter | More result options → select | 3 within mode | Results exist; discoverable via filter command |
| Search diagnostics | Quick actions → Search snapshot and provenance | 2 | Results exist; opens both enclosing disclosures |
| Ranking / candidate counts | Ask → Find passages if needed | 1–2 | Search results exist; scores are not a common scale |
| Inspect passage / original source | Result → source link | 1 / 2 within mode | Retained, authorized original required; source not available for every result |
| Structured region / raw extraction | Result → Raw extraction output | 1 / 2 within mode | Typed evidence object exists |
| Ordinary PDF highlight | Result → Passage on original page | 2 within mode | Exact retained glyph/text alignment; otherwise an explicit limitation |
| Add/remove shortlist selection | Shortlist passage | 1 within mode | Result exists; six-item cap; temporary collection session |
| Compare shortlist | Quick actions → Evidence shortlist | 2 | Opens nested shortlist; adding passages is a prerequisite |
| Inspect comparison-table citation | Shortlist command → citation | 3 | Table cell links focus retained passage with its own snapshot |
| Remove shortlist item / Undo | Shortlist command → Remove; Undo | 3 / 1 | Shortlisted item exists |
| Export shortlist | Quick actions → Export evidence shortlist → Export evidence | 3 | Nonempty shortlist; preserves question, snapshot and methods |
| Per-item shortlist provenance | Shortlist command → provenance | 3 | Item exists |
| Provider / standalone follow-up | Quick actions → named control | 2 to focus | Native provider choice adds 2; remains discoverable in palette |
| Grant / revoke cloud consent | Ask → Answer if needed → consent action | 2–3 | Owner only; explicit action; selecting mode/provider never grants consent |
| Active model and local/cloud | Ask context | 0 | Visible with More collapsed; absence explained |
| Search saved questions | Quick actions → Find saved research | 2 | One collection-scoped, debounced paginated endpoint |
| Open saved answer | Saved research → run | 2 | Run listed; no conversation enumeration needed |
| Older saved results | Saved research → Older research | 2 | Cursor available; bounded page |
| Conversation selector | Saved research → Browse conversations → select | 4 | Indexed: Quick actions → Browse conversations focuses selector in 2; native choice adds 2 |
| Inspect citation / original | Citation → source link | 1 / 2 within displayed run | Citation reauthorized; original may be unavailable |
| Used versus retrieved evidence | Quick actions → Based on — used and retrieved evidence | 2 | Completed answer displayed; actual claim/comparison IDs, not shortlist membership |
| Cancel / reconnect run | Cancel run / Reconnect | 1 within run | Active / disconnected run respectively |
| Four answer exports | Quick actions → Export saved answer as format → Export | 3 | Completed run selected; authorization retained |
| Replay pinned/current | Quick actions → replay choice → Replay | 3 | Inactive run selected; may invoke provider; command only reveals control |
| Run provenance | Quick actions → Saved run provenance | 2 | Run selected; More run options opens automatically |
| Close overlay / focus return | Close or Escape | 1 | Existing native dialogs/nonmodal inspector behavior retained |
| Dark mode / reduced motion | OS preference | 0 in app | No new preference storage |

Quick actions remain discoverable even when a result/run is missing. Choosing one explains the prerequisite rather than silently submitting a request. These counts describe reaching a capability with its data available, not generating missing evidence, finding a run across arbitrary pages, or completing external sign-in.

Backend experiments, deployment, ingestion administration, and training commands are developer/operator facilities, not hidden browser destinations. This plan preserves them and does not invent UI controls for all CLI operations.

## Approved navigation

**Three top-level destinations: Ask · Sources · Saved research.** Collection selection remains global context, not a fourth destination. Quick actions remain globally accessible. The Settings-sheet sketch below is historical; a new settings system is outside this implementation. On mobile, keep all three destination controls visible.

| Destination | Visible by default | Progressively disclosed |
| --- | --- | --- |
| Ask | One question composer, explicit Answer / Find passages mode, result or answer, evidence count and “Based on” action | More: retrieval method, Boolean syntax, standalone follow-up query, provider; result filters; diagnostics; shortlist |
| Sources | Add documents, review queue, processing stages, readiness and access summary | Collection details: snapshot IDs and operational details; archive in collection actions |
| Saved research | Searchable saved questions/runs with status and date; select a run directly | Run More: four export formats, pinned/current replay, detailed provenance |

Use Answer initially only when generation is configured and permitted; otherwise clearly select Find passages and explain how to enable answers. Never grant cloud consent implicitly. Keep the active model and cloud/local indication visible even when the selector is in More. Preserve comparison mode and exact retrieval references; proposal is natural-language hybrid for new passage searches, with explicit Compare methods available in More. This changes the initial UI selection, not server/experimental defaults, and is part of the approval decision.

Overview is **removed as a standalone destination**, not removal of its capabilities: onboarding and next action move into the current task, readiness/access into the collection header and Sources, technical metadata into collection details. Separate Search and Cited answers destinations are merged into Ask modes. No feature, export format, research history, comparison method, provenance field, consent control, or replay capability is proposed for removal.

```text
Collection selector                         Quick actions   Settings
Ask | Sources | Saved research

Question                                      Evidence side pane
[question input                         ]     Based on: 6 passages
Answer / Find passages       More    Ask      Selected passage + page
Answer with citation links                    Original + highlight
Based on: 6 passages                           Provenance / limitations
```

### Reachability contract

From any destination in the selected collection: destination (1), More/disclosure (2), action (3). Existing saved runs become Saved research (1), run (2), citation or run action menu (3). Deeper contextual actions, such as exporting a previously unopened run in a chosen format, must also be indexed in quick actions: search a saved question, choose its export action, then format. The three-click bound is for reaching a feature with its prerequisites available, not entering content or generating missing data.

Quick actions must include destinations, collection selection/creation, upload focus, composer focus, passage search, comparison, filters, shortlist, saved-run lookup, exports, provenance, and applicable recovery actions. Context-dependent actions disclose their required state instead of silently disappearing. Search of saved research must be authorized and collection-scoped; existing conversation-only run retrieval needs a scoped listing/search facility for direct access. Do not implement this with unbounded requests to every conversation.

## Original core loop and implementation requirements

The remaining requirements preserve the 2026-09-29 design rationale. They are not a claim that every proposed backend or keyboard-help feature was introduced by phase 2. Current navigation paths and verified coverage are recorded above and in AUDIT.md.

1. Enter question and submit. Preserve typed input on failure. Snapshot, provider identity, and consent are fixed for the run.
2. Show named phases immediately: queued, retrieving evidence, generating, checking citations. Skeletons reserve layout; status text remains available to assistive technology.
3. Stream real server events. Existing `/runs/{id}/events` returns finite resumable SSE batches; current UI polls run objects. This is not token streaming. Add bounded provider streaming only where supported, with resumable event IDs, cancellation, session/resource reauthorization, and reconnect fallback. Unchecked partial text must be explicitly provisional; final cited claims publish only after existing structural/citation checks. Never simulate streaming by animating a completed response.
4. Render compact inline citation anchors. Hover **or keyboard focus** opens a dismissible preview; click/Enter selects the same passage in a shared evidence side pane. Touch uses tap. Preview fetches must preserve authorization and prevent stale responses across collection/run changes.
5. One consistent “Based on” control lists the evidence used for that answer, distinguishes used evidence from retrieved candidates, and exposes snapshot/model provenance. The shortlist remains a separate user selection; it must not imply those passages generated the answer.
6. Show original source at its real locator. Retained structured evidence already supports region highlights. Ordinary PDF passages currently have page ranges but no exact highlight mapping: ingestion must retain trustworthy text offsets/boxes tied to the source revision. Do not guess coordinates or highlight an unrelated match. Missing locators show the retained passage with an explicit limitation; support rotation, zoom, and multipage regions when adding the viewer.
7. Close the pane without losing composer, results, scroll, or focus. Mobile uses an accessible sheet with a clear return action; desktop uses a nonmodal pane.

## State specification

| State | Intended experience |
| --- | --- |
| First visit, no collection | One primary action: Create collection; then Add documents |
| Collection without sources | One primary action: Add documents; explain supported formats/limits |
| Loading | Content-shaped skeletons, aria-busy and concise live status; respect reduced motion |
| Large PDF processing | Real named stages and file/batch state; use percentages only when backend provides a truthful denominator |
| No passages | Explain no match; keep question editable and offer another phrasing |
| Filter excludes everything | Clear filters action; distinguish from no retrieved evidence |
| Insufficient support | Show supported material and limitations; do not manufacture an answer |
| Model unavailable / consent absent | Explain why Answer is unavailable; Find passages stays available; explicit setup/consent route |
| Network failure / offline | Preserve drafts; show Retry/reconnect; never label network failure as logout or assume navigator.onLine proves availability |
| Authorization changes | Clear protected evidence and require reauthorization; no offline cache that bypasses access checks |
| Partial upload failure | Show each file's confirmed outcome; retry only safely identifiable failed/unconfirmed operations with correct idempotency |
| Partial retrieval/provider failure | Identify unavailable portion; never present incomplete comparison as complete; preserve supported results only if API semantics permit |
| Export/source unavailable | Inline explanation and retry/open-original fallback when valid; keep research context |
| Cancellation | Confirm stopped work accurately; generation cancellation can still incur provider cost |

## Keyboard and undo

Keep Cmd/Ctrl+K and Escape. Add Cmd/Ctrl+Enter to both composer modes. All common actions are searchable commands with visible shortcut hints in accessible tooltips; avoid intercepting typing, IME composition, native browser shortcuts, or screen-reader keys. Provide a keyboard-help entry. Scope Escape to the topmost active overlay, restore focus, and keep tooltips nonessential to understanding an action.

For local shortlist/queued-file removal, retain the removed value and position for an Undo action; never persist raw files to browser storage just for undo. Announce feedback without stealing focus.

The original proposal considered delayed archive versus explicit restore. The inherited implementation uses immediate archive and explicit Undo restore: access returns, but cancelled processing does not restart. Phase 2 preserves that lifecycle and its tests. Cloud-consent revocation and cancellation remain immediate; Undo never silently restarts paid generation or restores consent.

## Delivery boundaries and acceptance

After navigation approval, finish the shared tokens/components from Plan 1, then deliver separately reviewable changes: navigation/context; Ask composer and disclosure; scoped saved-run access; shared citation pane and preview; real event delivery; trustworthy locators/viewer; state handling; keyboard and undo lifecycle. Streaming, locator ingestion, archive lifecycle, and scoped listing require backend changes and focused authorization/concurrency tests, not just styling.

Acceptance: preserve all mapped capabilities; at most three top-level destinations as proposed; every feature within three activations given prerequisites or discoverable through quick actions; keyboard/touch parity; deterministic focus return; no unreviewed experimental default changes; no loss of snapshot isolation or consent; no fabricated progress/highlights; verify desktop/mobile/light/dark and error states after implementation. Plans 1 and 2 remain separate commit-sized work; no implementation begins merely because this document exists. Plan 3 has not yet been supplied.

**Approval recorded:** Ask / Sources / Saved research navigation, unified Ask modes and progressive disclosure were approved by the owner. Phase 2 completes their browser implementation on the phase-1 branch from main. Natural-language hybrid was already the initial passage-search selection in that base; this phase does not change retrieval defaults. See AUDIT.md for actual checks and unverified integration/manual gates.
