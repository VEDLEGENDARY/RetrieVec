# Paper workspace verification — 2026-10-14

The user flow is a private research collection → paper upload → ingestion →
searchable library → original source and passage search. The local application
starts through the default Compose stack or an OS-specific launcher.

## Verified

| Boundary | Evidence |
|---|---|
| Frontend build | TypeScript and Vite production build pass. |
| Browser behavior | Full 41-test UI suite passes, including screen inventories, contrast measurements, dark/light themes, reduced motion, mobile reflow, and keyboard behavior. Final library retry and logout-routing changes are covered by an additional targeted run. |
| API | Paper-library tests verify authentication before queries, live collection access, parameterized literal filename filtering, bounded cursor input, response fields, and empty pages. OpenAPI contract regenerated and checked. |
| PostgreSQL | New integration test passes against PostgreSQL 18 in an isolated schema: real upload rows, cursor pages, literal `%`/`_` filtering, private/curated access, and immediate archive revocation. Schema cleaned up by the test harness. |
| Repository checks | `scripts/check.py` passes: design tokens, Go formatting/vet/tests/build, Python dependency check, Ruff lint/format, and 181 Python tests (23 service/platform-dependent skips). |
| Windows launcher | Start, doctor, status, logs, stop, stopped engine, wrong container mode, and failed startup exercised with a fake Docker command. Failed starts do not announce readiness; stop does not delete volumes. |
| POSIX launcher | Shell syntax check passes; two behavior tests pass on Linux inside the container with fake Docker calls. |
| Real installation | `start.ps1` builds the image and starts the default stack. Workspace readiness and Keycloak readiness pass. Existing starter data and volume names are reused. |
| Real browser flow | Two Docker browser tests pass: real Keycloak registration, retained SciFact hybrid search and sign-out; private text-paper upload, library filtering, original source integrity response, and the handoff to passage search. |
| Dependency audit | Updated `source-map-js` from 1.2.1 to 1.2.2 within the existing dependency range; npm reports zero vulnerabilities. |

## Scope and limits

The browser fixture tests use synthetic HTTP data; they make no retrieval-quality
claims. The real upload smoke test also explicitly labels its input as synthetic
interface verification text. The starter corpus remains 24 SciFact abstracts,
without full-paper PDFs or a generation provider. Existing source/snapshot
integrity and cloud-consent checks remain authoritative.

The whole Python suite's database, pgvector, and specialized integration skips
are reported by the harness; the new paper-library database test was additionally
run against the real container database. No new schema migration is introduced.
No generated-answer or full-PDF extraction quality improvement is claimed.

The source-map dependency patch addresses
[GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q).
Existing upstream deprecation messages (Authlib/Starlette httpx and Lucide's
Vite `use client` directives) remain warnings; checks and builds complete.
