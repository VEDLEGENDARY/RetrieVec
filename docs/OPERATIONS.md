# Deployment and development

## Architecture

React presents the research workspace through same-origin FastAPI requests.
Python handles ingest, model adapters, consent-checked generation and workers;
Go handles query analysis, indexes, sparse/dense retrieval and fusion. PostgreSQL
holds ownership, sessions, jobs and saved runs. Immutable artifacts retain source,
chunk, model and snapshot identities. Retrieval RPC enforces scope independently
of the API. Generation is optional and does not change source authorization.

## Requirements

Native development requires Python 3.13, Go 1.26, Node.js 24, npm and PostgreSQL 18. The workspace requires an OpenID Connect provider. Docker builds the image; Kubernetes is the deployment path described below.

Sparse and exact retrieval run on CPU. Generation is optional. Store model weights and papers under ignored directories; never commit credentials, sessions, downloaded papers or private answers.

## Container image

The multi-stage `Dockerfile` builds React, Go and Python, then runs the workspace as an unprivileged user. Build it locally for a smoke test:

```bash
docker build -t retrievec:local .
```

For Kubernetes, push the image to a registry and deploy it by immutable digest. The default `compose.yaml` runs the complete local paper workspace. Use `compose.database.yaml` when native development only needs PostgreSQL. `compose.identity.yaml` starts pinned local Keycloak after generating its ignored realm file. See the [getting started guide](GETTING_STARTED.md) for local installation and first use.

## Native setup

### Windows PowerShell

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r python/requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e ./python
Push-Location web
npm ci
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

Run from the repository root with your Python virtual environment activated.
Stop the Docker demo first if it occupies ports 8000/8080. Set a private
`RETRIEVEC_DB_PASSWORD` in your shell before starting PostgreSQL; Compose requires
it. A local `.env` can supply Compose values, but Python does not load that file
automatically: also export the application settings in every service terminal.

Start PostgreSQL:

```bash
docker compose -f compose.database.yaml up -d postgres
```

Set `RETRIEVEC_DSN`, set `RETRIEVEC_PRINCIPAL=*`, and migrate:

```powershell
$env:RETRIEVEC_DSN = "postgresql://retrievec:$env:RETRIEVEC_DB_PASSWORD@127.0.0.1:55432/retrievec"
$env:RETRIEVEC_PRINCIPAL = "*"
.\.venv\Scripts\python.exe -m retrievec.registry.cli migrate
```

On Linux/macOS, use:

```bash
export RETRIEVEC_DSN="postgresql://retrievec:${RETRIEVEC_DB_PASSWORD}@127.0.0.1:55432/retrievec"
export RETRIEVEC_PRINCIPAL='*'
python -m retrievec.registry.cli migrate
```

Use a URL-safe database password, or percent-encode it in the DSN if it contains
URI-reserved characters. The decoded password must match PostgreSQL's password.

Generate the development Keycloak realm and start it:

```bash
python scripts/configure_identity.py
docker compose -f compose.identity.yaml up -d
```

The generated accounts are `researcher-a` and `researcher-b`; their random
passwords are in ignored `artifacts/identity/local-passwords.json`. Registration
is disabled for this native development realm. Keep those files private and
reuse them on later starts; the configuration script refuses to overwrite them.

Use the same environment in the API and worker terminals:

```text
RETRIEVEC_LOCAL_HTTP=1
RETRIEVEC_ORIGIN=http://127.0.0.1:8000
RETRIEVEC_OIDC_ISSUER=http://127.0.0.1:8080/realms/retrievec
RETRIEVEC_OIDC_CLIENT=retrievec
RETRIEVEC_STORE=artifacts/store
RETRIEVEC_FRONTEND=web/dist
RETRIEVEC_RPC=127.0.0.1:8092
RETRIEVEC_PRINCIPAL=*
```

Set `RETRIEVEC_READ_TOKEN` and `RETRIEVEC_WORKER_TOKEN` to distinct random strings
of at least 24 characters and use the same values in all service terminals.
Set `RETRIEVEC_ENGINE` to the absolute path of the engine built by
`scripts/check.py`: `artifacts/bin/retrievald.exe` on Windows or
`artifacts/bin/retrievald` on Linux. With `RETRIEVEC_FRONTEND=web/dist`, the API
serves the built UI; without it, the API alone does not serve the workspace.
Build the UI:

```bash
cd web
npm ci
npm run build
cd ..
```

Then run each service in its own terminal:

```bash
python -m retrievec.runtime rpc
python -m retrievec.app.worker
python -m retrievec.app.research_worker
python -m retrievec.app.main
```

Open `http://127.0.0.1:8000`. Health is available at `/healthz`. Keep RPC, database and model ports private. For UI development, `npm run dev` starts Vite with API/auth proxies.

## Corpus CLI

Build the engine and set `RETRIEVEC_ENGINE` to its absolute path. Put sources in ignored storage such as `artifacts/papers`.
For the bare `retrievald` commands below, add the absolute `artifacts/bin` directory
to your shell's `PATH`, or replace `retrievald` with the executable's full path.

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

To enable it for the native workspace:

1. Install a pinned llama.cpp server and obtain a compatible GGUF model in ignored
   local storage. Neither the native setup nor the Docker demo downloads a
   generation model. The example describes Qwen2.5 1.5B; it is a configuration
   template, not a claim that its model file is present or accurate.
2. Start the model server with its `/tokenize` and `/completion` endpoints on a
   private address, and a context window matching `context_tokens` in the provider
   configuration. Keep it running while generating answers.
3. Copy `configs/generation.local.example.json` to
   `artifacts/generation/providers.json` (create the directory first). Set
   `endpoint`, `model`, `revision`, context/output limits and timeout to match the
   actual server. Verify the GGUF hash; do not retain the example revision if you
   use a different file. If the server needs an API key, keep its environment
   variable name in `api_key_env` and supply the value only to the research worker.
4. Set `RETRIEVEC_GENERATION_CONFIG` to the absolute path of that JSON file in both
   the API and research-worker terminals, then restart those two services. Copying
   the example alone does not enable generation.
5. Sign in, select a searchable collection and choose **Answer** in Ask. Confirm
   the provider/model shown beside the composer, submit a question and inspect
   its citations. A cloud provider requires explicit collection consent first.

For containers, the configuration file and model endpoint must be accessible
inside the workspace container, and the configuration environment variable must
be passed to its runtime. Local providers require loopback HTTP: run the model
server in the worker's network namespace (for example, the same Kubernetes Pod),
not at `host.docker.internal` or an arbitrary service hostname. A host-only path
or host `127.0.0.1:8095` cannot be copied unchanged into the container.
The shipped demo Compose profile does not configure
this wiring; use your deployment configuration rather than assuming answers are
enabled by its startup command.

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

Native processes can install
`python -m pip install -e "./python[app,telemetry]"` and set `RETRIEVEC_OTEL=1`,
`RETRIEVEC_OTEL_ENDPOINT=http://127.0.0.1:4318/v1/traces`, and optionally
`RETRIEVEC_OTEL_SAMPLE_RATIO` between 0 and 1 (default 0.1). Restart after changes.
Tracing is disabled by default. Run a collector and Jaeger separately when those
services are needed. The sample collector configuration in `deploy/otel/` uses
bounded memory and queues.

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
docker build --check .
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

### Kubernetes deployment

The Kubernetes renderer targets a Linux k3s node with the `local-path` storage class
and NetworkPolicy enforcement. For another cluster, select an enforcing CNI and pass
its storage class with `--storage-class`. This is a single-node deployment with
restart downtime, not a high-availability service.
Do not scale the workspace replica count: worker locks and local storage require it.

The cluster must have `kubectl`, an enforcing CNI, a storage class, and an HTTPS
hostname with an OIDC provider. First verify the selected cluster and its storage
class:

```powershell
kubectl config current-context
kubectl get nodes
kubectl get storageclass
```

Build and push a Linux image for the cluster architecture, then copy its immutable
digest from the registry:

```powershell
docker buildx build --platform linux/amd64 --push `
  -t YOUR_REGISTRY/retrievec:YOUR_TAG .
```

Render the deployment with the immutable image digest:

```bash
python -m retrievec.deployment --image YOUR_REGISTRY/retrievec@sha256:YOUR_DIGEST \
  --origin https://research.example.com --issuer https://identity.example.com/realms/retrievec \
  --storage-class YOUR_STORAGE_CLASS --output artifacts/deploy/workspace.json
```

Create the namespace before creating its secrets:

```bash
kubectl create namespace retrievec
```

Register `https://research.example.com/auth/callback` with the OIDC provider.
Create `private/db-password` with the PostgreSQL password and
`private/workspace.env` with the following keys; replace all placeholders and
keep both files outside Git:

```dotenv
RETRIEVEC_DSN=postgresql://retrievec:YOUR_ENCODED_PASSWORD@postgres:5432/retrievec
RETRIEVEC_READ_TOKEN=YOUR_DISTINCT_RANDOM_TOKEN_AT_LEAST_24_CHARACTERS
RETRIEVEC_WORKER_TOKEN=ANOTHER_DISTINCT_RANDOM_TOKEN_AT_LEAST_24_CHARACTERS
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
exposed. PostgreSQL requests half a CPU and has no CPU limit, allowing it to use
spare node capacity during query bursts; benchmark your workload before changing
the request or memory limit. Back up both PostgreSQL and artifact storage before
upgrades. Local-path volumes stay on their node; replacing that node requires a
restore.

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
filesystem group. Native setup passes PostgreSQL credentials as separate libpq
environment variables so punctuation in passwords is not interpreted as URI syntax.

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
| Container unhealthy | Inspect Kubernetes pod events and logs with `kubectl -n retrievec describe pod` and `kubectl -n retrievec logs deployment/workspace` |
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


Before changing defaults, freeze the real corpus, held-out queries and reviewed
judgments; capture p50/p95 latency, throughput, failures, memory and disk under stated
resource/concurrency limits; then rehearse restore, interrupted jobs, database loss
and rollback on the target deployment. No benchmark numbers or acceptance results
are implied by this checklist. Do not substitute fixture vectors for quality evidence.

Develop on focused feature branches and merge into protected `main` through reviewed pull requests with visible, unsquashed commits. Keep dependencies pinned, preserve data provenance, and report measurements with their actual corpus, split, configuration and limitations.
