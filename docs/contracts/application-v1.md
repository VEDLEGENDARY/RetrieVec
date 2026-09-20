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
