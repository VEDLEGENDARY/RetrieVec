# Local RetrieVec workspace

Build the engine with `python scripts/check.py`. Install application dependencies
with `python -m pip install -r python/requirements-dev.txt` and reinstall the
package using `python -m pip install --no-build-isolation --no-deps -e ./python`.

Use the PostgreSQL 18 Compose service and set `RETRIEVEC_DSN`. Run registry
migrations with the existing CLI. Generate the private development identity realm
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

No generation, conversations or exports are included in steps 1–7. Existing
reviewed-relevance and real-corpus quality gates remain open.
