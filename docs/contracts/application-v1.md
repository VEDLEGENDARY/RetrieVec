# Workspace API v1

The FastAPI application publishes `/api/v1/openapi.json`. Authentication and
resource authorization are required before workspace routes are mounted. Go RPC
remains internal. Errors have `code` and a safe `message`; input bodies, database
errors and source paths are never reflected in errors.

Migrations are additive and idempotent. Existing principal ownership remains
unchanged; external identities must be explicitly linked by an operator when
migrating an existing local principal. No email-based ownership reassignment.

Steps 8–14 (conversation execution, generation, streaming and exports) are not
exposed by this batch. Their resource tables reserve ownership relationships.

Private collections allow only owners. Curated collections allow authenticated
reads; their owner is the designated curator and sole manager. Only operators
can designate curated collections. Archive revokes all access immediately and
fences/cancels ingestion. Physical purge is a separate operator operation.

For the workspace, set the Go RPC `RETRIEVEC_PRINCIPAL` to `*`. Authenticated
Python service calls must then assert the session-derived principal in internal
metadata. Go independently checks live ownership, curated access and archive
state. The read credential cannot prepare snapshots. Legacy fixed-principal
mode remains supported; service credentials never reach browsers.
