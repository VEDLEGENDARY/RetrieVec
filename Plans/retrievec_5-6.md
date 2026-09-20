# RetrieVec: Weeks 5–6 Handoff

## Required engineering workflow

Read and follow [ENGINEERING_WORKFLOW.md](ENGINEERING_WORKFLOW.md) in full before changing the repository. Its approval boundaries are part of this handoff.

- Work on only the first incomplete commit-sized step.
- Obtain approval for the proposed branch before creating or switching to it.
- Never implement or commit directly on `main`/`master`; integrate only through an approved pull request.
- After implementation and validation, present the diff, checks, limitations, and exact message; obtain approval before committing.
- Obtain separate authorization before pushing, opening/updating a pull request, merging, or starting the next step unless that exact action is already authorized.
- Use natural, project-focused branch names, commit messages, code, comments, documentation, and PR descriptions. Do not add tool attribution or fabricated authorship/review.
- Preserve unrelated changes and record actual evidence and incomplete gates honestly.
## Objective and prerequisites

Build an authenticated research workspace over the persistent hybrid engine: private collections, uploads with progress, retrieval comparisons, source inspection, cited synthesis, saved conversations/experiments, and exports.

Read both earlier plans, repository instructions, and `docs/IMPLEMENTATION_STATUS.md`. RetrieVec is the earlier name; use RetrieVec in the product while preserving existing package/format identifiers. Verify snapshot consistency, ingestion recovery, gRPC, and sparse/dense/hybrid evaluation before depending on them. Repair prerequisite gaps rather than replacing working subsystems.

Development remains local on 16 GB shared RAM, approximately 2–3 hours/day. The schedule is a guide; complete acceptance gates before declaring the milestone done. Use established identity/model libraries, retain existing conventions, and keep the repository private.

## Product experience

```text
Sign in → select private/shared collection → upload text PDFs
        → inspect processing progress → ask a question
        → compare sparse/dense/hybrid results → open cited source page
        → generate supported claims/comparison → save and export
```

Keep “Paper evidence” and “RetrieVec measurements” visibly separate. The application may summarize reported results, but cannot claim to reproduce a paper merely because it measured a related retrieval method.

Required: authentication, collection isolation, functional upload/search/source UI, grounded generation with abstention, persisted history/runs, and export. Defer OCR/tables/equation/chart understanding, collaborative teams, public sharing, scheduled monitoring, training, ANN, arbitrary repository execution, and deployment. Show unsupported document types/statuses honestly.

## 1. Application boundaries

```text
Browser: TypeScript + React workspace
   │ same-origin HTTP/JSON and streamed progress
Python API: identity, authorization, collection actions, search, generation, exports
   ├─ PostgreSQL: ownership, sessions/identity mapping, conversations, runs, citations
   ├─ existing ingestion worker and immutable artifact store
   ├─ Go gRPC sparse retrieval
   ├─ exact dense search / RRF
   └─ configured generation provider
```

Use the existing frontend framework if present; otherwise use React/TypeScript with a small development build setup. Keep business logic and authorization in Python. A same-origin development proxy simplifies browser sessions; document its configuration. Go stays internal.

## 2. Authentication and authorization

Use an established OpenID Connect implementation with a local development identity provider or an existing compatible project integration. Select and pin the implementation after reviewing current official documentation; do not invent a password reset/token system. Use Authorization Code with PKCE and a server-managed browser session. Map stable issuer/subject pairs to principal IDs, not email alone.

Require state/nonce and callback/issuer/audience checks through the chosen library. Store provider secrets/tokens server-side. Browser session cookie is HttpOnly, appropriately SameSite, Secure under HTTPS, with expiration and logout invalidation. Restrict any non-Secure cookie exception to explicit localhost development. Protect state-changing cookie-authenticated routes against CSRF; do not use wildcard credentialed CORS.

No development identity bypass in the normal application mode. Tests can inject principals through test-only dependency wiring. Provide two seeded development users for isolation tests without committing real credentials.

Authorization policy:

| Resource | Access |
|---|---|
| Private collection | Owner only |
| Curated collection | Authenticated read; designated curator manages content |
| Upload/job | Collection owner or explicit curator scope |
| Conversation/run/export | Creator; source access checked on every read |
| Corpus/source/citation | Authorized collection and allowed snapshot, including historical access policy |

Derive principal from the session and resolve collection scope server-side. Check ownership before enqueueing jobs or contacting retrieval. An object UUID/hash is not authorization. Apply the same checks to polling, streaming, downloads, citation resolution, and saved historical runs. Cross-user resource lookups should not disclose existence; use consistent not-found responses where appropriate.

Cache keys include principal/authorized scope, snapshot, query, model, and configuration. Initial implementation may avoid answer caching. Do not share private extracted text or generated answers through global caches.

The weeks 3–4 configured principal becomes a normal owned identity through a documented migration, not automatic ownership of all imported content by every user.

## 3. Metadata additions and lifecycle

Add migrations for identity mapping/sessions as required by the selected library, conversations, messages, generation runs, claims/citations, and export records. Reuse collection/job/snapshot tables.

- Conversation records have owner, collection, title, and timestamps.
- Each answer/run pins a retrieval snapshot; a conversation may contain runs against different snapshots, labeled individually.
- Messages record role and status; runs record effective query, retrieval configuration, model/revision, prompt version, evidence IDs, and errors.
- Claims record support status and cited chunk/page references; model-generated citation IDs must resolve through saved evidence.
- Store original question and any resolved follow-up query separately.
- Retain immutable run artifacts; changes create a new run/version, not silent rewrites.

Collection deletion/revocation immediately blocks access, cancels eligible pending work, and invalidates sessions' cached permissions. Physical artifact purge is a separate documented operation; do not promise immediate erasure or replay after purge. Default UI can archive collections in this milestone. Restore/replay requires authorization and artifact availability, not just a saved ID.

## 4. API contract

Version Python application routes independently from internal RPC. Publish OpenAPI and generate or maintain typed browser clients.

| Route | Behavior |
|---|---|
| `GET /api/v1/me` | Current user/session summary |
| `GET, POST /api/v1/collections` | List permitted collections / create private collection |
| `POST /api/v1/collections/{id}/uploads` | Bounded multipart upload → 202 job ID |
| `GET /api/v1/jobs/{id}` | Authorized status/stage/progress/error |
| `POST /api/v1/search` | Collection, question/mode, retrieval config → pinned results |
| `GET /api/v1/sources/{id}` | Authorized source content/metadata; no arbitrary path input |
| `GET /api/v1/citations/{id}` | Saved evidence passage and original-page locator |
| `POST /api/v1/conversations` | Create owned research thread |
| `POST /api/v1/conversations/{id}/runs` | Validate, pin, enqueue bounded generation → run ID |
| `GET /api/v1/runs/{id}` | Persisted run state/result |
| `GET /api/v1/runs/{id}/events` | Authorized progress/event stream |
| `POST /api/v1/runs/{id}/cancel` | Cooperative cancellation |
| `POST /api/v1/runs/{id}/exports` | Produce selected export from stored evidence/result |

Search separates parser mode (`free_text`/`structured`) from retrieval mode (`sparse`/`dense`/`hybrid`). Keep structured mode sparse-only until a complete filtered dense contract exists. Expose unsupported combinations as validation errors, not hidden fallback.

Validate uploads by bounded bytes and file signature as well as extension. Initial configurable limits: 25 MiB/file, 100 pages/file, 10 files/batch, one heavy ingestion task at a time on the laptop. Enforce per-user storage/job quotas and extraction timeouts. Use server-generated storage keys; sanitize display names; never execute uploaded content. Parsing occurs in a worker with bounded resources. Encrypted/scanned/unextractable PDFs return actionable statuses. Upload acknowledgment means accepted for processing, not searchable.

Serving sources must not bypass authorization through static artifact URLs. Use an authenticated source route compatible with PDF loading/range requests as needed. Never expose filesystem locations to the browser.

## 5. Research interface

Build a usable, responsive three-area workspace:

| Area | Content |
|---|---|
| Collection navigation | Private/shared collections, upload action, document/job status |
| Research canvas | Question, answer claims, method-comparison rows, saved runs |
| Evidence inspector | Ranked passages, source PDF/page, retrieval diagnostics |

Minimum screens/states:

- Sign in/out and empty collection onboarding.
- Upload progress with stage, retryable/terminal failures, and searchable confirmation.
- Search with three-mode side-by-side ranks, original scores labeled by type, source metadata, and snapshot ID.
- Source preview positioned to available page; show passage beside page when exact bounding boxes do not exist.
- Answer with clickable citations, insufficient-evidence state, provider failure, and cancel/retry.
- Saved conversations/experiments with replay as a new run and export actions.

Avoid fabricated processing percentages; show stage and known counts when total work is unknown. Do not present cosine/BM25/RRF values on a shared numeric scale. Preserve query/results when switching evidence panels. Include keyboard navigation, visible focus, associated form labels, readable contrast, mobile stacking, and accessible progress announcements.

## 6. Grounded generation contract

Implement a provider interface for local and explicitly enabled cloud models. Choose an actual model after measuring memory/latency and inspecting current model license/documentation. Core search remains useful if no generation model is available. Full milestone acceptance requires at least one real-provider demonstration; deterministic fixtures only establish plumbing.

Provider configuration records model/revision, endpoint, prompt version, generation parameters, tokenizer/context policy, and local/cloud status. Private-content cloud processing is off by default; the user must enable it for the collection/provider. Explain that passages and relevant conversation context will leave the local system. Student credits are not consent to send private documents.

Generation stages:

1. Authenticate and authorize collection access.
2. Resolve any follow-up into a stored standalone effective query; show it in diagnostics.
3. Pin one retrieval snapshot, retrieve candidates, and optionally rerank only through an explicit configuration.
4. Select a bounded evidence packet with stable evidence IDs, exact passage text, paper metadata, and page locators.
5. Fit evidence/history within the actual provider token budget, reserving output capacity. Record excluded/truncated passages.
6. Request structured claims and comparison rows referencing only supplied evidence IDs.
7. Validate schema, evidence membership, quote spans, and source availability before displaying final cited claims.
8. Persist status, evidence, prompt/model/configuration identifiers, and result before completion is announced.

Suggested output shape:

```text
status: answered | insufficient_evidence | partial
claims[]: {id, text, evidence_ids[], support_status}
comparisons[]: {
  method, dataset, metric, reported_value, experimental_conditions,
  limitations, evidence_ids[], comparability_note
}
limitations[]
```

Use “not reported in retrieved evidence” for missing conditions/values. Distinguish a paper-reported number from a number in a RetrieVec run. Do not rank incomparable methods as a universal winner. Evidence-ID validity and exact-quote matching do not prove semantic support; show them as structural checks, and measure support through human review.

Retrieved papers are untrusted data. Delimit them as evidence, never as instructions; generation has no shell, filesystem, network, or account-action tools. Escape model output when rendering and reject unsafe links/HTML. A malicious passage must not alter provider settings, expose another collection, or trigger tool calls.

Abstain when relevant evidence is absent or requested comparisons lack support. Structural validation failure gets a bounded repair attempt or explicit failure, not silently fabricated citations. Optional general background explanation is a separate labeled mode without implying paper support.

## 7. Streaming and run reliability

Use a persisted run state machine: `queued → retrieving → generating → validating → completed`, with `failed` and `cancelled`. Apply the existing lease/fencing approach to background generation if using workers. Do not hold database transactions open across inference.

Stream stage events and validated claim units; avoid displaying unvalidated token-level citations as final evidence. Events have run ID, monotonic event ID, type, and payload. Client reconnect reads persisted state and can resume buffered events or refetch a state snapshot without creating another model call.

Idempotent create-run requests prevent duplicate expensive execution. Store retry lineage. Cloud timeout outcomes may be uncertain; do not promise exactly-once provider billing. Bound retries and concurrency. Cancellation propagates through retrieval/model adapters where supported; late responses cannot overwrite a cancelled run. Revoked access terminates future reads/streams.

## 8. Saved work and exports

Save conversations, exact retrieval configurations, evidence selections, and generation results. Replay creates a new run against the explicitly selected historical/current snapshot; missing retained artifacts produce an explicit error. LLM outputs need not be byte-identical, even with identical configuration. Preserve the original result for comparison.

- Markdown: question, answer/claims, citations, limitations, snapshot/model identifiers.
- BibTeX: only known source metadata with escaped fields and stable keys; omit unknown DOI rather than invent one.
- JSON: versioned structured result/configuration/provenance.
- CSV: retrieval/experiment rows with defined columns and spreadsheet-formula injection protection.

Exports use the same authorization and stored evidence as the UI. Generate safe filenames and expiring/private downloads; do not embed private local paths, access tokens, or public artifact links.

## 9. Quality and security evaluation

Retain retrieval benchmark conventions from earlier milestones. Add a small owner-reviewed answer set, initially 12–20 questions, including unsupported comparisons, no-answer cases, follow-ups, and prompt injection inside documents.

Report separately: structurally valid citation rate, human-reviewed claim support, citation completeness, unsupported numerical claims, abstention behavior, task completion, generation latency/failures, and sample counts. Generated self-grades are supplemental, not human review. Do not tune on the final evaluation questions without recording reuse.

Mandatory tests:

| Test | Required behavior |
|---|---|
| User B requests A's job/source/run/export/citation | Denied without source disclosure |
| Search with another user's collection/snapshot | Denied before retrieval |
| Cached answer/stream after access revocation | No further private content served |
| Source contains prompt instructions | Treated as evidence, no privileged actions |
| Provider invents citation ID or quote | Rejected/marked invalid, never linked as verified |
| Snapshot activates during generation | Retrieval and evidence remain pinned |
| Browser reconnects/retries run creation | No duplicate run from same idempotency key |
| Cancel/revoke during inference | Late completion cannot publish an accessible answer |
| Oversized/invalid PDF or hostile filename | Bounded rejection and no path traversal |
| Missing model, provider failure, empty collection | Clear recoverable UI state |

Use deterministic provider fixtures for offline CI, plus a separately recorded real-model smoke run. Browser integration tests should exercise Python and test data, not only mocked UI responses. Manually inspect desktop/mobile layouts and keyboard flows before completion.

## 10. Fourteen commit-sized steps

Each step contains its implementation, meaningful tests, and documentation in a separate commit. Group related commits into reviewable PRs, preserving the logical history. Request human answer review early; do not mark reviews complete on the owner's behalf.

| Step | Commit message | Deliverable and validation gate |
|---|---|---|
| 1 | `feat: add Python application API and resource schemas` | Reuse search/ingestion modules, OpenAPI, error envelopes, migrations |
| 2 | `feat: integrate OIDC sessions and principal mapping` | Local identity setup, login/logout, callback/session/CSRF tests |
| 3 | `feat: enforce collection ownership across resources` | Two-user isolation, curated read policy, source/run access checks |
| 4 | `feat: add bounded private upload and job endpoints` | Resource limits, ownership, worker handoff, progress/failure tests |
| 5 | `feat: build authenticated collection workspace` | React/TypeScript shell, session flow, collection CRUD subset, accessibility |
| 6 | `feat: display upload and ingestion progress` | Real polling/progress, retry states, searchable confirmation |
| 7 | `feat: add retrieval comparison and source inspector` | Three-mode ranks, authenticated PDF access, snapshot diagnostics |
| 8 | `feat: persist conversations and research runs` | Owned history, pinned snapshots, idempotency, replay-as-new-run |
| 9 | `feat: add configured evidence-grounded generation` | Provider interface, consent boundary, token budgets, structured fixtures |
| 10 | `feat: validate claims citations and comparison evidence` | Evidence IDs/quote validation, abstention, untrusted-input tests |
| 11 | `feat: stream recoverable research run progress` | Persisted events/status, reconnect, cancellation and late-response tests |
| 12 | `feat: add cited answer views and research exports` | Citation interaction, saved-run UI, Markdown/BibTeX/JSON/CSV downloads |
| 13 | `test: evaluate answer quality and workspace isolation` | Browser flows, two-user attack matrix, reviewed answers, real-provider demo |
| 14 | `docs: deliver reproducible research workspace handoff` | Local setup, provider configuration, limitations, report, week-7–8 backlog |

Do not expose application routes before their authorization dependencies work. A frontend-only demonstration or fixture-only generation does not satisfy the full milestone.

## Acceptance and handoff

- Two users can sign in and use separate private collections; all alternate resource paths enforce isolation.
- Text PDFs upload asynchronously and become searchable only after successful snapshot activation.
- Search comparison and evidence inspection use real backend data and stable source links.
- A real generation provider produces reviewed cited answers; unsupported claims and missing evidence are handled explicitly.
- Saved runs retain provenance; reconnect, cancellation, replay, and exports behave consistently.
- Offline CI and integrated browser checks pass; desktop/mobile/keyboard flows are inspected.
- `docs/reports/week-06-workspace.md` records review counts, actual results, provider/hardware, limitations, and reproduction commands.
- Update implementation status and carry unresolved work forward explicitly. No public deployment is required.

Demo: sign in as A → upload → compare retrieval → inspect PDF → generate cited comparison → save/export → sign in as B and demonstrate isolation → show no-evidence response and reconnect/cancel behavior.

Weeks 7–8 follow-up: broader failure/load testing, performance profiling, expanded reviewed evaluation, reproducibility documentation, polished portfolio demo, release preparation. Advanced extraction and training remain separately evaluated extensions.

## Implementation task prompt

> Read this handoff completely, then read Plans/ENGINEERING_WORKFLOW.md, prerequisite plans, repository instructions, and implementation status. Follow every approval boundary. Work only on the first incomplete commit-sized step: propose its branch, scope, checks, and commit message, then wait for branch approval before changing code. After approval, implement and validate only that step, present the complete diff and results, and wait for commit approval. Do not work directly on main, push, open or merge a pull request, or begin another step without the required authorization. Keep repository language natural and project-focused, preserve unrelated work, and report actual evidence and incomplete gates.
