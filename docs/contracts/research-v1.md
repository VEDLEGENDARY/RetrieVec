# Research runs v1

All routes require the current OIDC session. Mutations also require the same
Origin and session CSRF token. A resource's creator must still have live access
to its unarchived collection; knowing an ID never grants access.

| Route | Contract |
|---|---|
| `POST /api/v1/conversations` | Collection ID and bounded title; returns owned conversation |
| `GET /api/v1/collections/{id}/conversations` | Latest 100 conversations belonging to the caller |
| `GET /api/v1/conversations/{id}/runs` | Latest 100 immutable requests/results |
| `POST /api/v1/conversations/{id}/runs` | `Idempotency-Key`, question, optional explicit effective query, provider, retrieval, parent and snapshot choice |
| `GET /api/v1/runs/{id}` | Saved state, provenance and validated result |
| `GET /api/v1/runs/{id}/events` | Finite SSE batch, up to 100 events after `after` or `Last-Event-ID` |
| `POST /api/v1/runs/{id}/cancel` | Idempotent cancellation of active work; completed results are immutable |
| `GET /api/v1/citations/{id}` | Exact selected passage, checked source availability and pinned locator |
| `GET /api/v1/collections/{id}/providers` | Operator-configured models and collection consent state |
| `PUT` / `DELETE /api/v1/collections/{id}/providers/{name}/consent` | Owner-only grant/revoke for the exact provider hash |
| `POST /api/v1/runs/{id}/exports` | Completed-run Markdown, BibTeX, JSON or CSV; returns private download URL and expiry |
| `GET /api/v1/exports/{id}` | Reauthorized download, or 410 after expiry |

Run creation resolves the active snapshot once, or uses the parent's snapshot
when `snapshot="historical"`. Historical replay requires a parent from the same
conversation. The retained manifest must exist and match PostgreSQL. Repeated
keys return the original run even after snapshot activation; changed payloads
return 409. Changed provider configuration requires a new run and new cloud
consent. Missing provider/snapshot leaves search available and returns a safe
recoverable error. Generation requests accept free-text retrieval only.

States are queued, retrieving, generating, validating, completed, failed and
cancelled. Events contain run ID, monotonic event ID, type and payload. Reconnect
does not enqueue work. Completed answers appear only after persisted validation;
there is no unvalidated token stream. Failed/cancelled requests retry through
new-run creation with parent lineage, not mutation of the original request.

Answers contain status, claims, comparisons and limitations. Claims include
stable IDs, text, selected evidence IDs, exact quotes and `structurally_valid`
support status. Comparison fields distinguish paper-reported values and missing
conditions. The backend rejects unknown fields/IDs, altered quotes, unsupported
numerical literals, unsafe markup/links and inconsistent abstentions. These
checks do not prove semantic support, relevance or experimental comparability.
The result records `human_review="pending"` until a separate owner review exists.

Stored evidence includes exact text, title, known authors, paper/chunk identities,
page range, original source hash/ID and private citation ID. No secret, local
storage path or provider credential is included. CSV cells defend against formula
prefixes; BibTeX only contains known title/authors and never invents DOI/year.
Exports expire in twenty minutes; at most twenty unexpired exports per run are
retained. Operators may delete expired export rows during maintenance. Physical
source/run purge remains an explicit future retention operation.
