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

The browser keeps session lifetime and collection refreshes in `useWorkspace`,
separate from page layout. Signing out aborts outstanding collection reads, and
older refreshes cannot replace newer state. Mobile navigation uses a modal dialog;
quick actions expose keyboard selection through a combobox and listbox. Shared
color tokens and visible focus indicators apply across those controls.

Run `npm run test:ui` in `web/` for browser interaction tests with synthetic HTTP
fixtures. The full `npm test` suite exercises the PostgreSQL, RPC, and OIDC flow;
interaction fixtures do not replace those integration checks.

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

### Optional pgvector study

The experimental adapter lives in `retrievec.experiments.pgvector`; the product
continues to use its exact file-backed dense reference. Use an isolated PostgreSQL
18 study database with the vector extension (`compose.vector-study.yaml` pins the
official image by digest). Set `RETRIEVEC_DSN` to that database and populate it with
authorized, ready snapshots and their verified artifact store before benchmarking.

```bash
docker compose -p retrievec-vector-study -f compose.vector-study.yaml up -d
python scripts/benchmark_pgvector.py --initialize --store artifacts/study-store \
  --principal YOUR_PRINCIPAL --collection YOUR_COLLECTION --snapshot rs_YOUR_SNAPSHOT \
  --queries private/vector-queries.json --output artifacts/pgvector-report.json
```

The query file contains `configuration` matching the pinned embedding encoder,
`queries` containing unique `query_id`, encoded `vector`, and optional `judgments`
mapping chunk IDs to grades 0–3, plus `judgment_provenance`. Preserve the frozen
held-out split and paper versions; synthetic labels are not human review.

Backfill verifies source hashes, every persisted vector's float32 checksum and
external IDs before atomic publication. Each immutable snapshot/model/config has
its own table and HNSW index, avoiding cross-collection ANN filtering. Existing
indexes are retained. The CLI's `--initialize` is an explicit administrator action
in a separate experimental schema; it never runs with ordinary product migrations.
Builds are bounded to 100,000 vectors by default and 2,000 dimensions, with SQL
timeouts. Interrupted builds roll back and can be restarted.

Reports separate ANN recall from judged relevance, exact ranking parity, build or
verification time, p50/p95 latency, failures and on-disk bytes. Memory and controlled
cache experiments remain explicit missing measurements. Fixture parity tests do not
establish real-model quality. The recorded decision remains **retain the reference
pending review** until representative quality/resource evidence supports a change.

### Optional distributed tracing

Enable the collector and Jaeger alongside the app with:

```bash
docker compose -f compose.app.yaml -f compose.observability.yaml up --build -d
```

Open Jaeger at `http://127.0.0.1:16686`. Native processes can install
`python -m pip install -e "./python[app,telemetry]"` and set `RETRIEVEC_OTEL=1`,
`RETRIEVEC_OTEL_ENDPOINT=http://127.0.0.1:4318/v1/traces`, and optionally
`RETRIEVEC_OTEL_SAMPLE_RATIO` between 0 and 1 (default 0.1). Restart after changes.
Tracing is disabled by default. The sample collector uses bounded memory/queues;
Jaeger uses transient storage, so restarting it loses traces.

API requests propagate W3C traceparent through Python RPC into Go. Database connection
and worker tick spans are included. SQL, query text, source text, credentials,
exception messages and baggage are not captured. Enqueued ingestion/research jobs
persist only their W3C traceparent and resume that context when claimed, including
retries. Migration 008 adds nullable columns with a three-second lock timeout;
older code ignores them, so rollback does not require dropping any data.
Do not expose these unauthenticated local collector/UI ports publicly. Collector
startup and a full deployed trace still require a working Docker engine.

The versioned API contract is `contracts/openapi.json`. Regenerate it with
`python -m retrievec.contracts` after changing routes and review the diff. CI runs
`python -m retrievec.contracts --check` to reject drift. The export records browser
session and CSRF requirements, local schema references, and streaming limitations.
Some research responses currently have permissive schemas; a passing contract
check does not imply complete response validation.

For an isolated JSON mock, run `npm ci` then `npm run mock` in `contracts/`.
Prism listens on `127.0.0.1:4010`. It does not implement OIDC, private-scope policy,
model inference, or real SSE replay/cancellation; keep those end-to-end tests against
the actual application. Never send private research data to a mock server.

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

### Optional single-node Kubernetes

Docker Compose remains the reference deployment. The Kubernetes renderer targets
a Linux k3s node with the `local-path` storage class and NetworkPolicy enforcement.
For Minikube, select an enforcing CNI and pass its storage class explicitly. This is
a single-node deployment with restart downtime, not a high-availability service.
Do not scale the workspace replica count: worker locks and local storage require it.

Build/push the image to your registry, obtain its immutable digest, then render:

```bash
python -m retrievec.deployment --image YOUR_REGISTRY/retrievec@sha256:YOUR_DIGEST \
  --origin https://research.example.com --issuer https://identity.example.com/realms/retrievec \
  --output artifacts/deploy/workspace.json
kubectl create namespace retrievec
```

Provision `database-secrets` with key `password`, and `workspace-secrets` with
`RETRIEVEC_DSN`, `RETRIEVEC_READ_TOKEN`, `RETRIEVEC_WORKER_TOKEN`, and optionally
`RETRIEVEC_OIDC_SECRET`. Use a local private environment file or a secret manager;
never put secret values in command history or checked-in manifests. The DSN must
target `postgres:5432/retrievec` with user `retrievec` and the same database password.
Percent-encode special characters if using a PostgreSQL URI.

```bash
kubectl -n retrievec create secret generic database-secrets --from-file=password=private/db-password
kubectl -n retrievec create secret generic workspace-secrets --from-env-file=private/workspace.env
kubectl apply --dry-run=server -f artifacts/deploy/workspace.json
kubectl apply -f artifacts/deploy/workspace.json
kubectl -n retrievec rollout status deployment/workspace --timeout=300s
```

The deployment creates three PVCs, resource budgets, a nonroot/read-only workspace,
startup/readiness/liveness probes, and default-deny network policies. HTTPS egress
is allowed for the configured identity provider and model downloads; tighten it
with your CNI's domain policy or preloaded models where required. No RPC port is
exposed. Back up both PostgreSQL and artifact storage before upgrades. Local-path
volumes stay on their node; replacing that node requires a restore.

For HTTPS, install a maintained Gateway API controller and TLS certificate separately.
Create a Gateway named `retrievec` in `gateway-system` with an `https` listener,
permit routes from the application namespace, and label the controller namespace
`retrievec.io/gateway=true`. Render with `--gateway` to include its HTTPRoute.
Register the exact HTTPS OIDC callback shown in the authentication setup above.
The controller, certificate issuance and live OIDC flow require deployment validation.

Alternatively, use `deploy/tofu` to manage the rendered resources. Run `tofu init`,
commit the generated provider lockfile after reviewing checksums, and run
`tofu plan` with explicit `kubeconfig`, `context`, and absolute `manifest_path`
variables. Import an already-created namespace before the first plan. Do not manage
the same deployment with both `kubectl apply` and OpenTofu. Destruction is blocked
by lifecycle guards. State and plans stay local and may contain operational data.
OpenTofu initialization, provider locks, server-side dry-run, restore, and pod-kill
checks must pass before considering this path production-ready.

### Container roles and private RPC

The image accepts `workspace` (default), `api`, `rpc`, `ingestion`, `research`, or
`migrate` as its command. Run migrations before starting separate roles. The
workspace command stops all children if any required role exits, and allows 35
seconds for shutdown. Workers stop claiming new jobs on SIGTERM; interrupted jobs
remain governed by their database leases. Keep one ingestion and one research
worker: their database singleton locks intentionally reject additional instances.

`/healthz` checks API liveness; `/readyz` checks the database, collection table and
authenticated Go RPC readiness with bounded timeouts. Go exposes role-authenticated
gRPC health services `live` (process only) and `ready` (database pool available).
Readiness does not certify model availability
or retrieval quality. `RETRIEVEC_FRONTEND` selects the built frontend directory;
the image sets it to `/app/web/dist`. Persist `/app/artifacts/cache` for model downloads.

The image now uses UID/GID 10001. Before upgrading an existing deployment, back up
its data and ensure the artifact/cache volumes are writable by that identity;
older images used a distribution-assigned system UID. Kubernetes sets the matching
filesystem group. Compose passes PostgreSQL credentials as separate libpq environment
variables so punctuation in passwords is not interpreted as URI syntax.

Plaintext RPC accepts numeric loopback addresses only. For separate hosts, mount
a private CA and distinct server/client certificates, then set these variables in
each role's environment:

| Variable | Retrieval server | Python clients |
| --- | --- | --- |
| `RETRIEVEC_RPC_TLS_CA` | CA that issues client certificates | CA that issues server certificates |
| `RETRIEVEC_RPC_TLS_CERT` | Server certificate chain | Client certificate chain |
| `RETRIEVEC_RPC_TLS_KEY` | Server private key | Client private key |
| `RETRIEVEC_RPC_LISTEN` | e.g. `0.0.0.0:8092` | Unused |
| `RETRIEVEC_RPC` | Unused by server | DNS name matching the server certificate SAN |

All three TLS files are required together. The Go server requires TLS 1.3 and a
verified client certificate; role bearer tokens and collection authorization are
still enforced. No hostname-verification bypass is provided. Restart roles after
certificate rotation. Keep keys outside Git and restrict mounts to their own role.
This follows the [gRPC authentication model](https://grpc.io/docs/guides/auth/).

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

## Development workflow

### Infrastructure acceptance gates

`configs/infrastructure-study.json` records the baseline revision, required
provenance, proposed acceptance thresholds, and decisions for the expanded stack.
The new infrastructure is optional. Passing software tests establishes functional
behavior; it does not establish production capacity, real-model quality, or a
successful live deployment.

| Capability | Current decision |
| --- | --- |
| Containers, mutual TLS, tracing, OpenAPI tooling | Available, with automated functional checks |
| Kubernetes/OpenTofu/Gateway route | Deployment tooling available; live cluster, HTTPS identity and recovery rehearsal required |
| pgvector exact/HNSW | Experimental adapter and benchmark available; retain exact reference pending reviewed measurements |
| Kafka and Redis | Deferred until a measured bottleneck justifies their operational cost |
| Streaming retrieval/generated claims | Retain bounded RPC and progress plus validated final answers |
| HPA/multi-node workers | Deferred while singleton locks and node-local storage apply |

RetrieVec and AskUTD are separate projects. This repository has no AskUTD integration
work planned.

Before changing defaults, freeze the real corpus, held-out queries and reviewed
judgments; capture p50/p95 latency, throughput, failures, memory and disk under stated
resource/concurrency limits; then rehearse restore, interrupted jobs, database loss
and rollback on the target deployment. No benchmark numbers or acceptance results
are implied by this checklist. Do not substitute fixture vectors for quality evidence.

Develop on focused feature branches and merge into protected `main` through reviewed pull requests with visible, unsquashed commits. Keep dependencies pinned, preserve data provenance, and report measurements with their actual corpus, split, configuration and limitations.
