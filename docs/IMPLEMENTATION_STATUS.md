# Implementation status

Weeks 1–2 steps 1–10 remain merged. This continuation implements the remaining
software for weeks 1–2 steps 11–14 and all fourteen weeks 3–4 implementation steps.
The historical feature commits are preserved. The owner's README redesign is
retained; no package or stored-format rename was inferred from that edit.

## Delivered software

- Versioned evaluation questions, frozen development/held-out splits, draft/reviewed
  provenance validation, replayable metrics and sparse demonstration.
- Compressed RLSEG001 writer/reader, bounded decoding, corruption checks, on-demand
  disk postings, empty collections and global multi-segment ranking.
- PostgreSQL ownership/registry migrations, prepared/ready states, active-parent CAS,
  idempotent leased jobs, fencing, retries and recoverable local ingestion.
- Generated authenticated Python/Go RPC with explicit snapshot identity, ownership
  checks, separate control credentials, limits and cancellation.
- Pinned real MiniLM CPU adapter, checked embedding artifacts, exact block cosine
  search and snapshot-pinned RRF with separate sparse/dense/fused scores.
- Three-mode capture, restart demonstration, recovery fixtures and PostgreSQL CI.

## Validation, 2026-09-19

The preserved final worktree passes Go formatting, vet, all Go package tests and
build; Python dependency consistency, Ruff lint/format and 27 Python tests pass.
Three PostgreSQL/RPC tests require the database integration environment. Local
Docker did not start; hosted PostgreSQL 18 CI is the remaining integration gate.
Its actual outcome will be recorded in the PR before merge.

Real-model smoke passed using MiniLM revision
1110a243fdf4706b3f48f1d95db1a4f5529b4d41 with CPU ONNX inference, a 2-by-384 output
and explicit rejection of input exceeding 256 model tokens. Reproduce with
python scripts/smoke_model.py --output artifacts/runs/minilm-smoke.json.
The artifact records model/tokenizer checksums and software configuration.

The sparse and hybrid demos, Go race/fuzz checks, generated-binding consistency,
and live registry/worker/RPC integration are included in the final CI workflow.
See [week 2](reports/week-02-baseline.md) and
[week 4](reports/week-04-baseline.md) for commands and evidence limitations.

## Open acceptance gates

The 20-question synthetic pool is draft, not owner-reviewed. Real-paper judgment
review, corpus expansion beyond the original five-paper seed, and a reviewed
sparse/dense/hybrid quality comparison remain open. No quality superiority,
power-loss durability or broad performance claim is made. These evidence gates
prevent claiming unconditional completion of both plans despite the implemented
software. Generated candidate pools do not satisfy human review.

PR #15 passed Windows, Linux and PostgreSQL/RPC integration and merged to main.

## Weeks 5–6 continuation

The owner authorized steps 1–7 and the RetrieVec naming migration. Steps 8–14
remain deferred. The naming migration changes source packages, commands, RPC
namespace and environment variables while retaining immutable stored formats.
Each implementation step remains a separate commit; merge commits preserve them.

- Step 1: application factory, bounded request schemas, safe error envelopes,
  versioned OpenAPI and additive workspace migrations. Resource routes remain
  closed until authentication and authorization are installed.
- Step 2: Authlib OIDC, PKCE, pinned issuer, PostgreSQL browser sessions, rotation,
  expiration, logout and CSRF. Local Keycloak setup generates two private users.
- Step 3: live owner/curated policy, collection create/rename/archive and
  resource-specific ownership queries. Internal RPC independently checks the
  trusted service's principal assertion and blocks archived scopes.
- Step 4: bounded multipart originals, owner storage/job quotas, durable ingestion
  handoff, retained successful inputs, authorized polling and archive cancellation.
  Private extraction uses a 120-second subprocess and a 100-page PDF limit;
  one workspace worker holds a PostgreSQL advisory lock across heavy tasks.
- Step 5: React/TypeScript authenticated collection workspace, responsive layout,
  collection creation/archive, session expiry, accessible forms and focus states.
- Step 6: real multipart uploads and authorized polling; stage labels, automatic
  retry states and searchable confirmation reflect persisted job state, not
  fabricated processing percentages. Failed submission retains file selection.
- Step 7: authenticated three-mode comparisons pin one retrieval snapshot; result
  scores retain their separate meanings. The source inspector resolves originals
  through ownership plus snapshot membership, verifies hashes, and supports PDF
  range requests through the authenticated API. No raw artifact URLs are exposed.

Local checks for this batch pass: Go vet/tests/build, Python lint/format and 37
tests, plus TypeScript/Vite production build. Six database-dependent tests and
the real Python/Go/PostgreSQL browser flow run in CI because local Docker is
unavailable. Browser evidence uses a test-only signed OIDC issuer and deterministic
embeddings; it does not establish real-corpus retrieval quality. Final CI status
is recorded in the PRs. Steps 8–14 remain untouched.

Final review found and fixed an executable-module error-class mismatch: running
the API with `python -m` now uses the same safe errors as an imported factory.
The regression test exercises that actual entry point. Cross-user search is also
asserted to fail before creating an RPC client or reading a source artifact.
