# RetrieVec

> A private research workspace for turning local papers into searchable, citable evidence.

[![Go](https://img.shields.io/badge/Go-1.26-00ADD8?logo=go)](https://go.dev/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python)](https://python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?logo=postgresql)](https://postgresql.org/)

RetrieVec imports text and PDF research material, records its provenance in immutable snapshots, and exposes sparse, dense, hybrid, and experimental retrieval through a private web workspace. Researchers can search passages, inspect sources, save conversations, produce grounded answers with citations, and export reproducible evidence bundles without handing their corpus to a hosted search provider.

The repository is also an experiment workbench. Exact retrieval remains the reference while optional OCR, table and equation extraction, reranking, approximate vector search, and compacted sparse indexes can be compared against frozen datasets. Experimental adapters never silently replace the reference path.

## Capabilities

| Area | Capability | Guarantee |
| --- | --- | --- |
| Corpus | Text/PDF ingestion, advanced extraction, OCR adapters | Source hashes and extraction provenance |
| Sparse search | Positional index, BM25, Boolean and phrase queries | Deterministic ranking and external IDs |
| Dense search | Pinned embeddings and exhaustive cosine search | Exact search remains the reference |
| Hybrid search | Sparse/dense reciprocal-rank fusion | Snapshot and principal remain pinned |
| Research | Conversations, cited answers, exports | Citations resolve to retrieved passages |
| Experiments | Rerankers, ANN, compaction, benchmarks | Frozen configurations and split isolation |
| Privacy | OIDC, opaque sessions, CSRF, ownership checks | Go and Python enforce scope independently |
| Operations | Registry, fenced workers, backup, telemetry | Immutable artifacts publish atomically |

## Architecture

```text
Browser (React + Tailwind + Lucide)
                |
                | same-origin HTTP, OIDC/PKCE, CSRF
                v
FastAPI workspace  -------- PostgreSQL 18
     |       |                 registry, jobs, sessions,
     |       |                 conversations and results
     |       +---- ingestion and research workers
     |                         |
     +---- authenticated gRPC  |
                |              |
                v              v
          Go retrievald ---- immutable artifact store
          sparse / dense       snapshots, segments, vectors,
          hybrid / ANN         exports and experiments
```

Go owns analysis, parsing, BM25, positional indexes, segment readers and retrieval RPC. Python owns corpus preparation, the registry, workers, evaluation, model adapters and FastAPI. React builds to static assets served by FastAPI. PostgreSQL is authoritative for ownership, active snapshots, leases, sessions and application state.

| Path | Purpose |
| --- | --- |
| `engine/` | Go search, indexing, ranking and RPC |
| `python/src/retrievec/` | CLI, corpus pipeline, registry, app, workers and experiments |
| `web/` | React workspace and Playwright tests |
| `datasets/` | Synthetic fixtures, manifests and evaluation data |
| `configs/` | Optional model, ANN, extraction and generation configurations |
| `scripts/` | Builds, audits, benchmarks, backup and evaluation tools |
| `artifacts/` | Ignored binaries, models, snapshots and run outputs |

## Requirements

Native development requires Python 3.13, Go 1.26, Node.js 24, npm and PostgreSQL 18. The workspace requires an OpenID Connect provider. Docker Desktop or Docker Engine with Compose is sufficient for the container workflow.

Sparse and exact retrieval run on CPU. Generation is optional. Store model weights and papers under ignored directories; never commit credentials, sessions, downloaded papers or private answers.

## Docker quick start

The multi-stage image builds React, Go and Python, then runs as an unprivileged user. The workspace container starts migrations, loopback retrieval RPC, ingestion worker, research worker and API. PostgreSQL and artifacts use named volumes.

1. Create local configuration:

   ```powershell
   Copy-Item .env.example .env
   ```

   ```bash
   cp .env.example .env
   ```

2. Replace every placeholder. Use distinct random values of at least 24 characters for `RETRIEVEC_READ_TOKEN` and `RETRIEVEC_WORKER_TOKEN`. Set `RETRIEVEC_OIDC_ISSUER` to the issuer visible to the browser and register `${RETRIEVEC_ORIGIN}/auth/callback`.

3. Build and start:

   ```bash
   docker compose -f compose.app.yaml up --build -d
   docker compose -f compose.app.yaml ps
   docker compose -f compose.app.yaml logs -f workspace
   ```

4. Open `http://127.0.0.1:8000`, sign in, create a collection and upload sources.

5. Stop without deleting data:

   ```bash
   docker compose -f compose.app.yaml down
   ```

Add `--volumes` only when intentionally deleting the database and artifact volumes. `compose.yaml` starts only PostgreSQL for native development. `compose.identity.yaml` starts pinned local Keycloak after generating its ignored realm file.

## Native setup

### Windows PowerShell

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r python/requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e ./python
Push-Location web
node "C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js" ci
Pop-Location
.\.venv\Scripts\python.exe scripts/check.py
```

### Linux

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r python/requirements-dev.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps -e ./python
(cd web && npm ci)
.venv/bin/python scripts/check.py --race
```

The check script formats and tests Python, builds and tests Go, validates fixtures, and writes `retrievald` below `artifacts/bin`.

## Run the native workspace

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Set `RETRIEVEC_DSN`, set `RETRIEVEC_PRINCIPAL=*`, and migrate:

```powershell
$env:RETRIEVEC_DSN = "postgresql://retrievec:$env:RETRIEVEC_DB_PASSWORD@127.0.0.1:55432/retrievec"
$env:RETRIEVEC_PRINCIPAL = "*"
.\.venv\Scripts\python.exe -m retrievec.registry.cli migrate
```

Generate the development Keycloak realm and start it:

```bash
python scripts/configure_identity.py
docker compose -f compose.identity.yaml up -d
```

Use the same environment in the API and worker terminals:

```text
RETRIEVEC_LOCAL_HTTP=1
RETRIEVEC_ORIGIN=http://127.0.0.1:8000
RETRIEVEC_OIDC_ISSUER=http://127.0.0.1:8080/realms/retrievec
RETRIEVEC_OIDC_CLIENT=retrievec
RETRIEVEC_STORE=artifacts/store
RETRIEVEC_RPC=127.0.0.1:8092
RETRIEVEC_PRINCIPAL=*
```

Set distinct read/worker tokens and make `RETRIEVEC_ENGINE` the absolute engine path. Build the UI:

```bash
cd web
npm ci
npm run build
cd ..
```

Then run each service in its own terminal:

```bash
retrievald rpc --store artifacts/store --listen 127.0.0.1:8092
python -m retrievec.app.worker
python -m retrievec.app.research_worker
python -m retrievec.app.main
```

Open `http://127.0.0.1:8000`. Health is available at `/healthz`. Keep RPC, database and model ports private. For UI development, `npm run dev` starts Vite with API/auth proxies.

## Corpus CLI

Build the engine and set `RETRIEVEC_ENGINE` to its absolute path. Put sources in ignored storage such as `artifacts/papers`.

```bash
python -m retrievec import --manifest datasets/manifests/seed-papers-v1.json --source-root artifacts/papers --output artifacts/snapshots
python -m retrievec validate-snapshot artifacts/snapshots/SNAPSHOT_ID
retrievald inspect --corpus artifacts/snapshots/SNAPSHOT_ID
retrievald --corpus artifacts/snapshots/SNAPSHOT_ID --listen 127.0.0.1:8091
python -m retrievec run --queries datasets/fixtures/queries-v1.jsonl --output artifacts/runs/example-01
```

Always use a new run directory. Runs capture configuration, rankings, timings and environment identity.

## Retrieval and data

| Mode | Reference | Use |
| --- | --- | --- |
| Sparse | BM25 over positional postings | Explainable lexical retrieval |
| Dense | Exhaustive cosine over pinned vectors | Exact semantic reference |
| Hybrid | Reciprocal-rank fusion | Broad default retrieval |
| Reranked | Frozen candidate pool | Optional measured experiment |
| ANN | Same vectors/query set as exact | Latency/resource experiment |

Every passage has stable external document and passage IDs, source hash, snapshot identity and extraction provenance. Snapshots are immutable. Activation changes a database pointer transactionally; pinned readers retain their original snapshot. Compaction writes new immutable output.

Evaluation data distinguishes draft, synthetic and human-reviewed judgments. Training, development and held-out splits must remain isolated across questions, paraphrases, document versions and evidence passages.

## Optional generation

Search works without a language model. Generation uses an operator-configured llama.cpp-compatible `/tokenize` and `/completion` service. Copy `configs/generation.local.example.json` into ignored storage, pin model/runtime revisions, verify artifact hashes, and expose the model only on loopback. Give the API and research worker the same `RETRIEVEC_GENERATION_CONFIG`; give only the worker the generation key.

The worker retrieves from a pinned snapshot, packs whole passages with the provider tokenizer, validates structured output, rechecks access, and atomically saves citations. Structural validation does not prove semantic quality; human answer review remains required.

## Experiments

Use committed configurations and unique artifact directories. Record corpus, query set, judgments, dependency/model versions, seed, parameters, hardware and failures.

```bash
python scripts/smoke_model.py
python scripts/compare_retrieval.py --help
python scripts/compare_ml_indexes.py --help
python scripts/benchmark_http.py --help
python scripts/review_evidence.py --help
python scripts/load_workspace.py --help
python scripts/freeze_evaluation.py --help
python scripts/compare_evaluations.py --help
```

Compare rerankers on identical candidate pools. Measure ANN recall against exact cosine separately from judged relevance. Optimize sparse search only after measuring a bottleneck and proving ranking/statistics parity. Negative results are valid; defaults change only after reviewed evidence.

## Validation

```bash
python scripts/check.py
cd web && npm run build
cd web && npm test
docker compose -f compose.app.yaml config --quiet
docker build -t retrievec:local .
```

CI runs supported Windows and Linux checks. Never mark model, browser, load or human-review gates as passed unless they ran against the stated configuration.

## Backup and restore

Stop writers or let active jobs finish:

```bash
python scripts/workspace_backup.py backup --store artifacts/store --output private/backup-01 --quiesced
python scripts/workspace_backup.py verify private/backup-01
```

Restore only into a fresh empty database named `retrievec_restore_<uuid>` and new artifact directory. Set `RETRIEVEC_RESTORE_DSN`, then:

```bash
python scripts/workspace_backup.py restore private/backup-01 --store private/rehearsal-01/store
```

Backups contain private corpus data and are not encrypted by this tool.

## Security

- Use HTTPS outside localhost and exact OIDC callback/origin values.
- Keep RPC, PostgreSQL and model servers private.
- Rotate read, worker, OIDC and generation secrets independently.
- Never commit `.env`, `private/`, papers, weights, backups or `artifacts/`.
- Preserve old snapshots while readers can reference them.
- Cancel through authenticated endpoints; do not rewrite job state manually.
- Treat exports and backups as private data.

## Troubleshooting

| Symptom | Resolution |
| --- | --- |
| Login loop | Match issuer, origin and callback; do not mix `localhost` and `127.0.0.1` |
| Database unavailable | Check PostgreSQL health and `RETRIEVEC_DSN`, then restart workers |
| RPC unavailable | Start `retrievald rpc`; verify tokens, store path and address |
| Upload remains queued | Check ingestion worker and absolute engine path |
| Research remains queued | Check research worker, generation config and key |
| Container unhealthy | Inspect `docker compose -f compose.app.yaml logs workspace` |
| Stale frontend | Rebuild `web/dist` with `npm run build` |
| Interrupted run | Inspect saved state and create a new run; do not mutate history |

## Contributing

Development reaches protected `main` through pull requests with visible, unsquashed commits. See [CONTRIBUTING.md](CONTRIBUTING.md). Report measurements with their actual corpus, split, configuration and limitations.
