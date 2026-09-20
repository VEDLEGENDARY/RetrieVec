# RetrieVec naming migration

The product and source packages are now RetrieVec (`retrievec` in identifiers).
Reinstall the editable Python package, rebuild the Go binary, and restart both
services together: the generated RPC service namespace has changed. Set the
`RETRIEVEC_*` environment variables in place of the previous prefix.

Existing corpus, snapshot, embedding identities and RLSEG001 bytes are unchanged.
Existing PostgreSQL databases and volumes need not be renamed: point
`RETRIEVEC_DSN` at the retained database. New Compose installations use `retrievec`.
Plan filenames have migrated together with their internal links.

Merge feature PRs with merge commits; do not squash or rewrite logical commits.
