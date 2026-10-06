# Release verification

## Recorded checks

- Required `scripts/check.py` ran with isolated PostgreSQL 18 and pinned pgvector
  Docker services: 146 Python tests passed, no skips; Go vet/tests/build, fixture
  audits, dependency consistency, formatting and lint passed.
- `npm run build` passed. Existing Lucide dependency directive warnings remain.
- `npm run test:ui -- --workers=2` passed all 30 tests after the final comparison
  changes, including every-cell citations, focus, removal/Undo, export, 390px
  dark-mode reflow and the full light/dark screen inventory.
- Real arXiv 2104.08663v4 import retained its source and metadata. DOI parsing
  and source binding use deterministic fixtures; a live DOI PDF was not imported.
- The Docker demo built and became healthy. Its real Keycloak registration,
  OIDC sign-in, default hybrid SciFact search and sign-out passed the dedicated
  Playwright demo test. No HTTP responses or identity tokens were mocked.
- The Qwen2.5 1.5B run recorded all 60 cases: 11 completed, 49 failed. Semantic
  accuracy, stronger-provider comparison, human review and NLI remain unverified.

## Clean-checkout README command verification

An independent detached checkout at `2f402f5` used a fresh Python environment
and fresh npm dependencies. The final isolated-output UI rerun used `f25970c`.
Both PostgreSQL services remained isolated; no database tests were skipped.

| README command | Actual result |
|---|---|
| `python -m pip install -r python/requirements-dev.txt` | Exit 0 in fresh environment |
| `python -m pip install --no-build-isolation --no-deps -e ./python` | Exit 0 |
| `python scripts/check.py` | Exit 0; 146 Python tests, no skips; Go/lint/format passed |
| `cd web` | Subsequent web commands ran from that directory |
| `npm ci` | Exit 0; independently installed node_modules |
| `npx playwright install chromium` | Exit 0; browser cache already present |
| `npm run build` | Exit 0 |
| `npm run test:ui -- --workers=2` | 30 passed in final clean rerun |
| `docker compose -f compose.demo.yaml --profile demo up --build -d` | Exit 0; fresh project volumes, healthy workspace/PostgreSQL, real Keycloak |
| `docker compose -f compose.demo.yaml --profile demo ps` | Exit 0; running services confirmed |
| `docker compose -f compose.demo.yaml --profile demo down` | Exit 0; volumes retained |

The fresh Docker project was selected with `COMPOSE_PROJECT_NAME` to avoid
reusing the initial demo's volumes. Docker build layers and the host Chromium
cache were reused; this is a clean source checkout, not a fresh machine. Native
checks used Python 3.13.15 and Node 26.1.0; the Docker frontend built on pinned
Node 24.14.0. On this Windows host, npm/npx commands were dispatched through
their installed Node CLI because the shell shim is broken. The npm commands ran;
the bare shell shim remains unverified. Relative README/design/release links and
the measured-table/250-line publication guard passed; the README has 116 lines.

An initial clean UI run hit two trace-cleanup errors when a concurrent demo run
cleared its shared output folder. The demo now has a separate ignored output
directory. The complete clean UI rerun passed all 30 tests without overlap; the
real clean-demo registration/search/sign-out test also passed.

No weights, credentials, .env files, paper PDFs, local skills or AGENTS.md appear
in the branch's changed-file list. The demo and evaluation private artifacts stay
outside Git. Release notes are a candidate; no tag or release has been published.

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

## Changed files and suggested PR description

The draft's file diff contains the full inventory. Principal changes are:

- `datasets/answer_quality/`, `scripts/evaluate_answers.py`,
  `python/src/retrievec/evaluation/answer_*.py`, `ANSWER_EVAL.md` and dated results.
- `corpus/sections.py`, `corpus/metadata.py`, `corpus/pdf_locations.py`, importer,
  pinned retrieval attributes, worker validation and authorized page-image route.
- `web/src/SectionField.tsx`, `PaperDetails.tsx`, `PassageLocation.tsx`,
  `EvidenceTray.tsx`, `Research.tsx`, associated types, styles and browser tests.
- `compose.demo.yaml`, `demo/`, Dockerfile and the actual-service demo test.
- `README.md`, screenshot, `docs/OPERATIONS.md`, moved design documents,
  `CHANGELOG.md`, candidate release notes and measured-report publication tests.

Suggested description: “Unify the research workspace and add provenance-bound
section filters, identifier metadata, verified PDF highlights and cited paper
comparison. Add a real-pipeline answer harness, local Keycloak/SciFact demo and
reader-focused release documentation. Preserve scoring, consent, authorization
and immutable snapshots; retain experimental variants as opt-in. Verified with
146 repository tests, 30 UI tests and real clean-demo sign-in/search/sign-out.
Qwen results remain synthetic/automatic-only; human review, NLI, stronger-provider
comparison and production deployment gates are unverified.”
