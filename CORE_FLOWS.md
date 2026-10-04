# RetrieVec core flows and navigation proposal

Date: 2026-09-29. **Navigation and implementation approved by the owner.** This document preserves the original flow inventory and proposal. The 2026-10-04 UI-unification phase builds on the navigation already merged into `main`; see [current audit status](AUDIT.md#implementation-update--2026-10-04) and [shared component contracts](docs/DESIGN_SYSTEM.md).

Current presentation uses Ask → Answer / Find passages, Sources, and Saved research. Answer composition is headed **Cited answers**. Collection details/readiness replace the old overview, and archive uses the existing Undo flow. UI unification retains the existing shortcuts, focus/Escape behavior, retry keys, session cleanup, consent rules, and research state machine; this phase does not approve or introduce further navigation or retrieval-default changes. The audit lists actual automated coverage and remaining manual/integration gates.

## One mental model

A collection holds sources. Ask questions of that collection, then verify each answer against its retained evidence. Saved research preserves the question, answer, model configuration, and source snapshot.

The three core jobs are:

1. **Add sources:** create/select a collection, add documents, understand when they are searchable.
2. **Ask questions:** get a cited answer or search passages directly, without configuring a retrieval experiment first.
3. **Verify evidence:** inspect the exact retained passage and its original source, assess limitations, and return to the answer without losing context.

These are inferred from the implemented product and the brief, not user-research findings.

## Current feature map and click counts

Source inspection: `web/src/main.tsx`, `Search.tsx`, `Research.tsx`, `Uploads.tsx`, `EvidenceTray.tsx`, `AdvancedEvidence.tsx`, and `CommandMenu.tsx`. Counts are source-derived, not measured usability sessions.

Starting point is the signed-in desktop Overview with an active collection. Count navigation/disclosure/action activations; exclude text entry, scrolling, waiting, and operating-system file-picker steps. Native select selection counts as opening plus choosing (2). Prerequisites are explicit: a result must exist before inspecting it. Mobile adds one activation for controls inside the collapsed collection navigation; workspace section tabs remain outside it. Counts describe reaching/using a feature, not the entire prerequisite workflow.

| Feature | Current path | Clicks | Prerequisite / caveat |
| --- | --- | ---: | --- |
| Sign in | Welcome → Sign in | 1 | External identity-provider steps excluded |
| Switch collection | Collection button | 1 | Mobile: 2 |
| Filter collections | Sidebar filter | 1 focus | Typing filters immediately; mobile: 2 |
| Create collection | Title field → Create | 2 | Mobile: 3; creation returns to Overview |
| Sign out | Sidebar → Sign out | 1 | Mobile: 2 |
| Archive collection | Archive → browser confirmation | 2 | Owner only; cancels active work; no restore UI |
| Overview / snapshot and access summary | Overview | 0 | Already on destination |
| Add sources | Sources → Choose documents | 2 | File selection excluded; drop is alternative |
| Submit selected documents | Sources → Upload documents | 2 | Valid files already selected |
| Remove queued file | Sources → Remove file | 2 | Local queue only; not uploaded-source deletion |
| Inspect file validation | Sources | 1 | Selected files show errors inline |
| Processing stages / automatic retries | Sources | 1 | Processing activity initially expanded |
| Retry unconfirmed upload | Sources → Upload documents | 2 | Same unchanged batch retains its request key; not a dedicated retry control |
| Search passages | Search → Search evidence | 2 | Enter question; active snapshot |
| Boolean/phrase query | Search → Query syntax → option | 3 | Forces sparse retrieval |
| Retrieval mode / compare all three | Search → Retrieval method → option | 3 | Comparison is current initial default |
| Cancel search | Search → Cancel search | 2 | Request in progress |
| Restore recent query | Search → Recent searches → query | 3 | Restores fields only; submit adds 1 |
| Compact/full excerpts | Search → Compact results | 2 | Results exist |
| Filter returned text | Search → filter field | 2 | Local filtering; no new search |
| Filter returned methods | Search → method select → option | 3 | Results exist |
| Ranking, scores, candidate counts | Search | 1 | Results exist; scores have different meanings |
| Snapshot/search configuration | Search → diagnostics | 2 | Results exist |
| Inspect a passage | Search → result | 2 | Opens evidence inspector |
| Open original source | Search → result → source link | 3 | Original retained and authorized |
| Embedded source preview | Search → result | 2 | Ordinary sources use iframe; no exact text highlight |
| Structured evidence and highlighted region | Search → result | 2 | Only sources with retained evidence-object locators |
| Raw structured extraction | Search → result → Raw extraction output | 3 | Structured evidence available |
| Shortlist / unshortlist passage | Search → Shortlist passage | 2 | Six-item limit; temporary collection session |
| Compare shortlisted passages | Search → Evidence shortlist | 2 | Add passages first |
| Remove shortlist item | Search → Evidence shortlist → Remove | 3 | No undo |
| Export shortlist JSON | Search → Evidence shortlist → Export | 3 | Includes original question and snapshot |
| Shortlist item provenance | Search → Evidence shortlist → provenance | 3 | Preserves per-item origin |
| Generate cited answer | Cited answers → Generate | 2 | Question, snapshot, configured/consented provider |
| Standalone follow-up query | Cited answers → query field | 2 | Separate from displayed question |
| Select model/provider | Cited answers → provider select → option | 3 | Configured providers only |
| Grant/revoke cloud consent | Cited answers → consent action | 2 | Selected cloud provider; owner only |
| Select existing/new conversation | Cited answers → conversation select → option | 3 | New conversation created on submission |
| Open saved run | Cited answers → conversation select → option → run | 4 | 2 if correct conversation is already selected |
| Inspect answer citation | Cited answers → citation | 2 | Run already displayed; citation reauthorized |
| Open citation's original source | Cited answers → citation → source link | 3 | Run already displayed |
| Comparison tables / limitations / support status | Cited answers | 1 | Completed run displayed |
| Cancel generation | Cited answers → Cancel run | 2 | Active run |
| Reconnect saved run | Cited answers → Reconnect | 2 | Retry budget exhausted |
| Export Markdown/BibTeX/JSON/CSV | Cited answers → export format | 2 | Completed run; authorization checked |
| Replay pinned/current snapshot | Cited answers → replay choice | 2 | Inactive run; may invoke paid provider |
| Run provenance | Cited answers → Run provenance | 2 | Effective query, snapshot, model revision |
| Find actions/collections | Quick actions → match | 2 | Cmd/Ctrl+K then typing/Enter alternative |
| Navigate sections via command palette | Quick actions → destination | 2 | Current palette lacks most contextual actions |
| Close inspector / citation / dialog | Close or Escape | 1 / key | Returns focus where supported |
| Keyboard search submission | Cmd/Ctrl+Enter in search field | key | Cited-answer composer lacks equivalent shortcut |
| Skip navigation | Keyboard skip link | key | Focuses main research area |
| System dark mode / reduced motion | OS preference | 0 in app | No manual in-app selector |

Backend experiments, deployment, ingestion administration, and training commands are developer/operator facilities, not hidden browser destinations. This plan preserves them and does not invent UI controls for all CLI operations.

## Approved navigation

**Three top-level destinations: Ask · Sources · Saved research.** Collection selection remains global context, not a fourth destination. Settings are a sheet reached from a persistent toolbar button; quick actions remain globally accessible. On mobile, keep all three destination controls visible.

| Destination | Visible by default | Progressively disclosed |
| --- | --- | --- |
| Ask | One question composer, explicit Answer / Find passages mode, result or answer, evidence count and “Based on” action | More: retrieval method, Boolean syntax, standalone follow-up query, provider; result filters; diagnostics; shortlist |
| Sources | Add documents, review queue, processing stages, readiness and access summary | Collection details: snapshot IDs and operational details; archive in collection actions |
| Saved research | Searchable saved questions/runs with status and date; select a run directly | Run More: four export formats, pinned/current replay, detailed provenance |

Use Answer initially only when generation is configured and permitted; otherwise clearly select Find passages and explain how to enable answers. Never grant cloud consent implicitly. Keep the active model and cloud/local indication visible even when the selector is in More. Preserve comparison mode and exact retrieval references; proposal is natural-language hybrid for new passage searches, with explicit Compare methods available in More. This changes the initial UI selection, not server/experimental defaults, and is part of the approval decision.

Overview is proposed for **removal as a standalone destination**, not removal of its capabilities: onboarding and next action move into the current task, readiness/access into the collection header and Sources, technical metadata into collection details. Separate Search and Cited answers destinations merge into Ask modes. No feature, export format, research history, comparison method, provenance field, consent control, or replay capability is proposed for removal.

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

## Core loop and implementation requirements

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

Archive currently immediately marks the collection archived and fences/cancels ingestion and research work (`app/resources.py`); there is no owner-facing unarchive endpoint. Replacing confirmation with a toast alone would be incorrect. Proposed design: server-backed pending archive with an undo interval, recoverable after reload, then atomic final archive/cancellation. The message must say when access/processing actually stops. Alternatively implement explicit restore with accurately limited semantics; restoring visibility cannot resume cancelled jobs automatically. Choose and validate one lifecycle before removing the existing confirmation. Cloud-consent revocation and cancellation must remain immediate; undo must never silently restart paid generation or restore consent.

## Delivery boundaries and acceptance

After navigation approval, finish the shared tokens/components from Plan 1, then deliver separately reviewable changes: navigation/context; Ask composer and disclosure; scoped saved-run access; shared citation pane and preview; real event delivery; trustworthy locators/viewer; state handling; keyboard and undo lifecycle. Streaming, locator ingestion, archive lifecycle, and scoped listing require backend changes and focused authorization/concurrency tests, not just styling.

Acceptance: preserve all mapped capabilities; at most three top-level destinations as proposed; every feature within three activations given prerequisites or discoverable through quick actions; keyboard/touch parity; deterministic focus return; no unreviewed experimental default changes; no loss of snapshot isolation or consent; no fabricated progress/highlights; verify desktop/mobile/light/dark and error states after implementation. Plans 1 and 2 remain separate commit-sized work; no implementation begins merely because this document exists. Plan 3 has not yet been supplied.

**Approval requested:** Ask / Sources / Saved research navigation, unified Ask modes, progressive disclosure, and natural-language hybrid as the initial passage-search selection. No application code or Git commits were changed for this proposal.
