# Repository cleanup — 2026-10-06

This maintenance change keeps the existing PR work and separate commits. History
is not rewritten, and unmerged branches/worktrees are retained. After the cleanup
was verified and pushed, the owner explicitly authorized all PRs to land through
regular, unsquashed merges after their checks pass. Remaining integration results
are recorded separately; this record does not claim unrun checks.

## What changed

- Three large measurement JSON files are replaced by byte-preserving gzip
  archives. Combined size is **93,066,212 → 46,651,499 bytes**, saving **46,414,713
  bytes** in the current checkout. Original and compressed hashes are recorded
  in [the archive manifest](results/archives-2026-10-06.json).
- A small offline report reader supports plain JSON and gzip. The packer refuses
  to overwrite existing archives, verifies decompressed bytes and checks that the
  source did not change before removing its duplicate. Report renderer, tests and
  publication links use the new archives. Measurements were not recomputed.
- Tailwind scans only app source and the entry HTML. Its resulting production
  assets match the prior build; no CSS size or runtime-speed gain is claimed.
- Docker build context excludes tests, documentation, contracts and experiment
  records that the Dockerfile does not consume. Tests remain in the repository.
- Root test output is ignored alongside the existing web output exclusions.
- Removed **7,017 generated files totaling 346,865,597 bytes** locally: Ruff
  caches, browser outputs, an idle Go build cache and 28 unreferenced one-off
  rewrite scripts/old PR text drafts. Absolute targets and reparse points were
  checked before deletion. No native Go compiler was running.

Model/dependency caches, source papers, evaluation stores, snapshots, credentials,
local environment files, current executable/frontend builds, skills and AGENTS
were retained. Their local exclusions remain intact. This work reduces checkout
and temporary-output size; old large blobs remain in Git history, so historical
clone size is not reduced.

## Files changed

Report packaging: `python/src/retrievec/evaluation/report_io.py`, its regression
tests, `test_beir_reporting.py`, the two BEIR renderers, the three dated result
archives and their hash manifest. Documentation: README/BENCHMARKS source links,
the phase-5 result link, `docs/results/README.md` and this record. Build hygiene:
`.dockerignore`, `.gitignore`, `web/src/style.css`.

## Verification

| Command/check | Result |
|---|---|
| Report archive regressions | Three passed: exact bytes/blank review fields preserved, existing archives protected, malformed data rejected. |
| Published BEIR report checks | Three passed; every published table and README number still matches. |
| `python scripts/check.py` with isolated PostgreSQL/pgvector | 152 Python tests, no skips; Go vet/tests/build, dependency checks, lint/format and token guards passed. |
| `npm run build` | Passed; CSS/JS asset hashes unchanged. Existing Lucide directive warnings remain. |
| `npm run test:ui -- --workers=2` | All 33 passed, including the 144-screen inventory and keyboard/consent/provenance checks. |
| Relative documentation links | No missing links in README/design/release documents. |
| `docker compose -f compose.demo.yaml --profile demo up --build -d` | Passed after retrying an interrupted base-image download/DNS failure. |
| Real Keycloak/demo browser test | One passed: registration, sign-in, hybrid search and sign-out. |

Windows checks used the installed npm/npx Node entry points. The Python check
runner supplied ignored private test DSNs. Generated local outputs were removed
after validation; the current frontend build remains available.

## PR completion and limits

PRs #49–53 had green checks before this cleanup. The verified changes are carried
into #53 through a regular local merge from the focused cleanup branch. This
does not merge any GitHub PR or flatten existing feature commits.

Human answer/PDF judgments, manual screen-reader/other-browser review, live
Kubernetes, production load and recovery rehearsal remain unverified. The
cleanup does not close those gates or label automatic measurements as human
review. Retrieval defaults, authorization, consent, original-source retention,
snapshot encoding/identities and API error codes are unchanged.

Suggested PR description addition: preserve all measurement bytes while reducing
current result-file size, constrain stylesheet/Docker inputs, remove generated
local clutter and keep the existing validated research workflows. Validation:
152 Python tests without skips, Go checks, build, 33 UI tests and real Docker
sign-in/search/sign-out; original hashes retained and publication tables unchanged.
