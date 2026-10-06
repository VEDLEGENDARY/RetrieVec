# Release verification

## Recorded checks

- Required `scripts/check.py` ran with isolated PostgreSQL 18 and pinned pgvector
  Docker services: 145 Python tests passed, no skips; Go vet/tests/build, fixture
  audits, dependency consistency, formatting and lint passed.
- `npm run build` passed. Existing Lucide dependency directive warnings remain.
- `npm run test:ui -- --workers=2` passed all 30 tests after PDF locations.
  After comparison changes, five workbench/saved-research tests passed, including
  every-cell citations, focus, removal/Undo, export and 390px dark-mode reflow.
- Real arXiv 2104.08663v4 import retained its source and metadata. DOI parsing
  and source binding use deterministic fixtures; a live DOI PDF was not imported.
- The Docker demo built and became healthy. Its real Keycloak registration,
  OIDC sign-in, default hybrid SciFact search and sign-out passed the dedicated
  Playwright demo test. No HTTP responses or identity tokens were mocked.
- The Qwen2.5 1.5B run recorded all 60 cases: 11 completed, 49 failed. Semantic
  accuracy, stronger-provider comparison, human review and NLI remain unverified.

Clean-checkout verification and the final complete UI rerun are pending at this
documentation commit. Their actual results will be recorded before finishing.

## Reproduce database-backed checks

Provide isolated PostgreSQL 18 services. `RETRIEVEC_TEST_DSN` enables application
and ownership integrations; `RETRIEVEC_VECTOR_TEST_DSN` enables pgvector tests.
Without them, the test suite reports skips; those are not passed database gates.
Keep credentials in your shell or ignored private files. The normal check command
is `python scripts/check.py`; the Go toolchain must be on PATH.

Start the demo using the README command, then run its actual service check:

```sh
cd web
npx playwright test --config playwright.demo.config.ts
```

The demo test creates an isolated local account with a generated password. It
does not send email, record traces containing credentials or change cloud consent.

Kubernetes was attempted: no current kubectl context is configured, and the
default API address refused connections. Cluster deployment, HTTPS production
identity, recovery rehearsals, concurrent-user capacity, manual screen-reader
checks and non-Chromium browser checks remain unverified. No production gate or
published release is implied by local verification.
