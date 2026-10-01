# Gap closure audit

Baseline: `f33868f`, 2026-09-30. This inventory precedes fixes. Stage 2 is held for owner review. The referenced master-prompt Part A was not attached; this audit follows the supplied Stage 1 requirements and repository instructions.

| Item | Status | Evidence | Fix plan |
| --- | --- | --- | --- |
| A1 Validated answer display | broken | `web/src/Research.tsx:721` renders selectable raw `progress.draft`; `research_worker.py:239` publishes unvalidated deltas | Stream stages/evidence only; remove raw draft publication and rendering |
| A2 Citation/export/saved validation | partial | `research_worker.py:263` constructs citations after validation; browser failure coverage missing | Add invalid-provider publication and DOM regression cases |
| A3 Scientific text acceptance | broken | `app/answers.py:157` broad angle-bracket/scheme regex rejects inequalities and ordinary `data:` | Explicit markup/URL recognition; 15+ cases |
| B1 Persistence inventory | done | `drafts.ts:19,64` localStorage; `Search.tsx:50,65` React state; `research.py:189` PostgreSQL runs | Inventory below |
| B2 Scope, expiry, ownership, migration | partial | `drafts.ts:26` expiry on read; `useWorkspace.ts:20` logout clearing; migrations 003/005/006; OpenAPI run-list path exists | Clear foreign-principal drafts on login; test expiry and scope, verify all saved endpoints |
| C1 Follow-up rewrite | missing | `research.py:324` uses manual override or original question only | Bounded server rewrite with consent/ownership, editable effective query |
| C2 URL routing | missing | `main.tsx` view is React state; no popstate/pushState | Linkable collection/view/run with reload and history |
| C3 Evaluate disclosure | partial | `Search.tsx:197` More contains retrieval controls; hybrid is default | Name Evaluate area and retain comparison diagnostics |
| C4 SSE stages and fallback | partial | `useRunProgress.ts:17` EventSource; Research polls state; migration 005 | Consume stage events as refresh hints, retain authorized polling |
| C5 Deliberate states and Undo | done | `web/ui-tests/archive.spec.ts`; `resources.py` owner-only restore; `rg window.confirm web/src` no matches; skeletons in main/Research/Search | Retain existing tests and confirm final regression suite |
| C6 Accessibility and keyboard | partial | UI tests cover navigation/citation focus; no axe dependency or per-view scans | Add pinned axe dev dependency, main-view/dialog scans and keyboard flow |
| C7 Design hygiene and modularity | partial | token stylesheet exists; Research 878 lines, Search 553, main 493, Uploads 323; no token lint | Extract coherent components; add CI lint with explicit geometry exceptions |
| D1 Immutable caching and RPC reuse | partial | `app/search.py:65` one RPC instance outside mode loop; `dense/hybrid.py:71,80` loads corpus twice per client; no shared artifact cache | Share validated immutable artifacts per request first; preserve resolve checks |
| D2 Partial top-k | missing | `dense/search.py:44` sorts every block candidate | Partition cutoff with deterministic external-ID ties; reference parity tests |
| D3 Chunk budget and overflow | partial | uploads 96 analyzer tokens; importer default 256; `dense/model.py:98` explicitly rejects >256 wordpieces | Measure pinned tokenizer overflow, document distinct token units; preserve rejection |
| D4 Search/answer benchmark | partial | `scripts/benchmark_http.py`; PERF contains browser and tiny model transport timings only | Measure representative HTTP workload if service available; report missing measurements explicitly |
| E Final quality gates | partial | PR46 at f33868f: Windows, Linux, PostgreSQL/RPC, container jobs all successful (GitHub API status) | Run requested local gates and require green final PostgreSQL CI; Linux race in CI |

## Persistence inventory

- Question and manual follow-up draft: localStorage `retrievec:draft:v1:<principal>:<collection>:<field>`; bounded in-memory fallback. Seven-day read expiry. No passages/answers stored here.
- Recent searches, shortlist, selected evidence, current result: React memory only; unmounted on logout/collection change. Shortlist export creates a user-requested download, not browser persistence.
- Saved research: PostgreSQL conversations, research_runs, evidence_citations, run_events, exports (migrations 003–006); retained artifacts in server store. Access is reauthorized via Resources. No IndexedDB/sessionStorage use found in `web/src`.
- Current view/collection/run selection: memory only at baseline; no reload/back restoration.

## Evidence limits

No local PostgreSQL DSN was configured during the preceding increment. CI is the database/service evidence. No full HTTP before/after search/answer latency measurement is claimed. Infrastructure tests and structural answer checks are not human relevance/support review.

## Closure evidence

Implementation commits: `e76f1ad`, `f43f364`, `e423e35`, `1be7933`. The original inventory above is retained as the before-state.

| Item | Current status | Evidence | Limits / remaining work |
| --- | --- | --- | --- |
| A1 | done | `research_worker.py` accumulates provider output privately; `useRunProgress.ts` has no draft listener; `Research.tsx` has no raw-draft rendering; legacy draft events are redacted by `research.py` | Only stages and retrieved passages stream; validated answers appear after completion |
| A2 | done | `exports.py:174` requires completed result; citations originate after `validate_answer`; `generation_fixture.py` emits invalid-answer sentinel; `web/tests/workspace.spec.ts` asserts failed run has no sentinel, citation or export controls | PostgreSQL service/browser CI passed at `1be7933`; retrieved passages can still be copied as source evidence, not model claims |
| A3 | done | `test_answers.py::test_scientific_prose_and_untrusted_markup_table`: 10 accept / 12 reject cases; five answer tests pass | Structural checks are not semantic correctness |
| B1 | done | Persistence inventory above remains accurate; URL fragments now add view/collection/run IDs, never question/answer/passages | Browser history retains identifiers, and opening a link still requires live authorization |
| B2 | done | `retainPrincipalDrafts`, `clearDrafts`, expiry-on-read including memory fallback; `drafts.spec.ts` covers expiry, collection isolation, foreign-principal cleanup, logout; `test_workspace_db.py` cross-principal routes; migrations 003–006 and updated `contracts/openapi.json` | No new tables required; saved runs reuse existing migrated schema |
| C1 | done | `query_rewrite.py::rewrite_query`, authorized `/runs/{id}/rewrite`, enqueue stores same bounded query; Searching for line with Edit action / Advanced override; unit and database tests | Deterministic one-parent question expansion, not model-based pronoun resolution. No additional model call or billing. Replays preserve explicit effective query |
| C2 | done | `routing.ts` fragment routing; `navigation.spec.ts` reload/back/forward; `saved.spec.ts` run deep-link reload; `useWorkspace` validates collection against authorized listing | No private text in URL; invalid/inaccessible IDs never authorize data |
| C3 | done | `Search.tsx:187` Evaluate retrieval disclosure; default hybrid retained; `SearchRankings.tsx` preserves all three score formats | Comparison scores remain different scales |
| C4 | done | `useRunProgress.ts` handles seven stage events as refresh hints; authorized run fetch remains publication source, timed polling remains fallback | SSE is finite resumable batches, not an indefinitely held connection |
| C5 | done | `archive.spec.ts` passes; first-run and skeleton states preserved; `rg window.confirm web/src` has no matches | Undo restores access, never cancelled work |
| C6 | done | axe 4.13.0 scans light/dark Ask/Sources/Saved, command dialog, mobile navigation and evidence inspector; 15 UI tests pass | Keyboard activation service test passed in CI; programmatic file selection is used for the native file chooser. No manual screen-reader certification |
| C7 | done | `scripts/check_design_tokens.py` invoked by `scripts/check.py`; shared Citation, researchTypes and SearchRankings extracted; all formatting checks pass | Remaining large orchestration files justified below; lint covers declarations, not every possible dynamically generated style |
| D1 | done | `test_request_artifact_cache.py` proves one corpus/embedding load across three clients and rejects revoked/other access with warm cache; one RPC instance remains outside comparison loop | Cache lifetime is one request. Cross-request artifact caching is deferred until memory/invalidation measurements justify it. Persistent embedding-build cache already keys text hash + full model config + role in `dense/artifacts.py` |
| D2 | done | `test_dense.py::test_partition_matches_full_sort_at_tied_cutoff` covers four k values and three block sizes; all five dense tests pass in full check | Sorting remains for cutoff ties and bounded final candidates; scores unchanged |
| D3 | done | `wordpiece-budget.json`, pinned tokenizer hash; 256-analyzer-token snapshots: 160/193 overflow each (82.90%); fresh 96-token import: 0/467, max 244 wordpieces; rejection-before-inference test | 96 analyzer tokens is not a universal 256-wordpiece guarantee. CLI retains reproducible 256 default; use explicit `--token-budget 96` for this measured MiniLM corpus. Encoder rejects rather than truncates |
| D4 | partial | Existing PERF browser/transport baselines are explicitly scoped; `scripts/benchmark_http.py` is available | No authenticated local service/PostgreSQL DSN for matched before/after search and answer HTTP runs. No HTTP latency numbers invented; remains an operational measurement gate |
| E | done | Local `scripts/check.py`: Go vet/test/build, lint, formatting, dependencies, 115 Python tests (19 skipped); contract check passed; build, 15 UI tests, Prettier passed | All PR checks passed at `1be7933`, verified 2026-10-01. Linux jobs run `--race`; PostgreSQL evidence is CI-only |

### Large-file decisions

`Research.tsx` retains asynchronous conversation/run orchestration, authorization-driven clearing, consent, and submission together for this increment; pure types and citation presentation were extracted. Splitting the remaining coupled effects without a state-machine redesign would risk duplicate requests and stale private results. `Search.tsx` retains request cancellation, draft/shortlist ownership and controls; ranking rendering is extracted. `main.tsx` owns session-aware workspace navigation; `Uploads.tsx` owns the bounded upload/retry lifecycle. Their >300-line size is an explicit exception, not a claim that all files meet a numerical limit. `style.css` is the shared stylesheet, with literals governed by the token checker. Further controller decomposition can follow as separately reviewed work.

### Reproduction

Run `python scripts/check.py` (`--race` on Linux), `python -m retrievec.contracts --check`, then in `web`: `npm run build`, `npm run test:ui`, `npx prettier --check src tests ui-tests`. Set `RETRIEVEC_TEST_DSN` only to an isolated PostgreSQL test database to exercise DB gates locally.

Wordpieces: `python -m retrievec import --manifest datasets/manifests/seed-papers-v1.json --source-root artifacts/papers --output artifacts/seed-snapshots --token-budget 96`, then `python scripts/measure_wordpiece_budget.py --corpora artifacts/seed-snapshots --output docs/reports/gap-closure/wordpiece-budget.json`. Requires the pinned tokenizer already cached; the measurement does not download a model.

