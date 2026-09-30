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
