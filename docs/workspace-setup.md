# Local RetrieVec workspace

Build the engine with `python scripts/check.py`. Install application dependencies
with `python -m pip install -r python/requirements-dev.txt` and reinstall the
package using `python -m pip install --no-build-isolation --no-deps -e ./python`.

Use the PostgreSQL 18 Compose service and set `RETRIEVEC_DSN` (the Compose host
port is 55432). Set `RETRIEVEC_PRINCIPAL=*`, then run
`python -m retrievec.registry.cli migrate` before starting services. Generate the private development identity realm
with `python scripts/configure_identity.py`, then start
`docker compose -f compose.identity.yaml up -d`. Two random local passwords are
written under ignored `artifacts/identity/`. Do not commit them.

For the default localhost application set:

```text
RETRIEVEC_LOCAL_HTTP=1
RETRIEVEC_ORIGIN=http://127.0.0.1:8000
RETRIEVEC_OIDC_ISSUER=http://127.0.0.1:8080/realms/retrievec
RETRIEVEC_OIDC_CLIENT=retrievec
RETRIEVEC_STORE=artifacts/store
RETRIEVEC_RPC=127.0.0.1:8092
RETRIEVEC_PRINCIPAL=*
```

Set distinct random `RETRIEVEC_READ_TOKEN` and `RETRIEVEC_WORKER_TOKEN` values
(at least 24 characters) and `RETRIEVEC_ENGINE` to the built engine's absolute
path. Start `retrievald rpc --store artifacts/store`, then
`python -m retrievec.app.worker` in a second terminal. Download/test the real
MiniLM model first using `python scripts/smoke_model.py`.

In `web`, run `npm ci` and `npm run build`. Start `python -m retrievec.app.main`
and open `http://127.0.0.1:8000`. The API serves the built UI on the same origin.
For frontend development, rebuild in watch mode or configure the Vite proxy and
explicitly register port 5173 as an OIDC callback and application origin. Do not
mix localhost and 127.0.0.1 in cookies or callback URLs.

## Local generation

Generation is optional; search and source inspection work without it. The tested
CPU configuration is llama.cpp **b11064**, Qwen2.5-1.5B-Instruct **Q4_K_M**, four
threads, no GPU layers, one slot and 4096 context tokens. The model is an
experimental local baseline: the [week 6 report](reports/week-06-workspace.md)
records both structural failures and visible semantic weaknesses.

Download the official [Windows CPU runtime](https://github.com/ggml-org/llama.cpp/releases/download/b11064/llama-b11064-bin-win-cpu-x64.zip)
and the pinned [model artifact](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q4_k_m.gguf)
into ignored `artifacts/generation/`. Extract the runtime into `llama-b11064/`.
Verify SHA-256 before use:

| Artifact | SHA-256 |
|---|---|
| Windows runtime ZIP | `7ab60d09ed43e365542297f1cf586e984fd56d84c491744cefda35070d768b96` |
| Model GGUF | `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e` |

On Windows PowerShell, generate a private server key without printing it:

```powershell
$env:RETRIEVEC_GENERATION_KEY = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:RETRIEVEC_GENERATION_KEY | Set-Content artifacts/generation/server.key -NoNewline
Copy-Item configs/generation.local.example.json artifacts/generation/providers.json
$env:RETRIEVEC_GENERATION_CONFIG = (Resolve-Path artifacts/generation/providers.json).Path
artifacts/generation/llama-b11064/llama-server.exe -m artifacts/generation/qwen2.5-1.5b-instruct-q4_k_m.gguf -c 4096 -t 4 -ngl 0 --parallel 1 --host 127.0.0.1 --port 8095 --no-webui --api-key-file artifacts/generation/server.key
```

Give both Python processes the same `RETRIEVEC_GENERATION_CONFIG`; give the
research worker `RETRIEVEC_GENERATION_KEY` (read the ignored key file in that
terminal). Restart the API after changing providers. Start
`python -m retrievec.app.research_worker` in another terminal with the same DSN,
store, RPC/read token and embedding settings. This is separate from the upload
worker. Never expose the model server or internal RPC publicly. Keep the server's
actual model artifact and context size aligned with the pinned configuration;
the operator verifies the artifact hash before starting it.

On Linux use the matching official b11064 CPU binary and equivalent environment
exports. Runtime archive hashes are platform-specific; the GGUF hash is shared.
The Python application and provider interface are identical on both platforms.

Remote generation currently means an operator-configured **llama.cpp-compatible
native `/tokenize` and `/completion` deployment**, not an arbitrary chat API.
Use `cloud: true`, an HTTPS origin, pinned model/revision and an `api_key_env`
containing only an environment-variable name. Redirects and ambient proxy
settings are disabled. The collection owner must explicitly allow the provider
in the workspace before any question/evidence is tokenized remotely. Changing
the endpoint/model/budget requires new consent. Revocation cancels active work.
Do not place credential values in provider JSON or commit the private key file.

## Operation and recovery

Use “Ask the evidence” after ingestion activates a snapshot. For a follow-up,
provide a standalone query when the question relies on earlier context. Saved
runs expose the original/effective question, snapshot and model revision. Replay
chooses current or historical data explicitly; it never overwrites the old run.
Missing retained artifacts fail rather than switching snapshots silently.

Each user may have three active runs. The research worker consumes one at a time;
240 seconds bounds token packing plus generation. A crashed/expired attempt
becomes `worker_interrupted` on the next worker scan. Retry creates a new run;
remote billing may have occurred even if the answer was never published. The UI
refreshes saved states and the event endpoint supports cursor reconnection.
Cancellation closes supported in-flight HTTP calls and fences late publication.

Exports are authenticated and expire in twenty minutes. Archive blocks access
and active work, but does not delete retained files. Back up PostgreSQL and the
artifact store together. Do not remove historical snapshot/source artifacts if
you still need replay or citation inspection. Automatic physical purge and
cross-service disaster recovery drills remain week 7–8 work.

## Reproduce checks

```text
python scripts/check.py
python scripts/check.py --race                 # Linux with a C compiler
cd web
npm ci
npm run build
npx prettier --check src tests playwright.config.ts vite.config.ts
npx playwright install chromium
npm test
```

Browser tests require an isolated PostgreSQL 18 database in `RETRIEVEC_TEST_DSN`
and `RETRIEVEC_ENGINE` pointing to the built Go executable. They start real Python
and Go services with a signed test-only OIDC issuer, deterministic embeddings and
a deterministic generation adapter. Those fixtures are not runtime provider
options and do not establish real-model quality. Hosted CI runs these checks;
local Docker/Keycloak was unavailable during this handoff.

With the real local server running, reproduce the separate synthetic model smoke:

```text
python scripts/smoke_generation.py --output artifacts/generation/smoke.json --revision sha256:6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e --runtime llama.cpp-b11064 --cpu "YOUR CPU" --ram-bytes YOUR_RAM_BYTES
```

Use actual hardware values and keep the key environment variable set. The
[answer review packet](reports/week-06-answer-review.md) remains unreviewed;
the owner explicitly deferred human acceptance. Existing real-corpus relevance
and answer-quality gates remain open.
