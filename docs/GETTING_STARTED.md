# Get started with your research papers

RetrieVec is a local research workspace: collect papers, search for passages,
inspect original sources, and export evidence for your writing. The starter
workspace includes 24 SciFact title/abstract records so you can try search before
uploading anything. These are abstracts, not full PDFs.

## Install and start

Install Git and Docker Desktop with Linux containers (Windows/macOS), or Docker
Engine with the Compose plugin (Linux). Start Docker before continuing. Compose
must support `include` and `up --wait` (Compose 2.20 or newer). No host Python, Go,
Node, model server, or database installation is needed.

```sh
git clone https://github.com/VEDLEGENDARY/RetrieVec.git
cd RetrieVec
```

On Windows, run this from PowerShell:

```powershell
.\start.ps1
```

On macOS or Linux:

```sh
sh start.sh
```

The launcher checks Docker, validates the Compose configuration, builds the app,
and waits for both the workspace and sign-in service to be ready. Your first
start needs internet access and may take several minutes to build images and
download the pinned MiniLM retrieval model. Later starts reuse cached files.
The launcher allows 15 minutes for service startup after the build. For a slow
first download, inspect the logs and retry the same command; volumes are reused.

The equivalent Docker command is:

```sh
docker compose up --build --wait --wait-timeout 900
```

Open [your workspace](http://127.0.0.1:8000). Use this address consistently for
sign-in and registration. Ports 8000 (app) and 8080 (local identity) must be free.
Both ports bind to your computer's loopback interface.

## Your first research session

1. Choose **Sign in to your workspace**, then **Register**. Create your own local
   account. Credentials are generated and retained in Docker volumes; no preset
   password or cloud consent is included.
2. Try the **SciFact starter** collection. In **Ask → Find passages**, enter
   `cancer` and choose **Search evidence**. Open a result to inspect its passage.
3. Create a private collection in the sidebar, for example **My literature
   review**. Creation takes you straight to **Sources**.
4. Drop PDF papers, text, or Markdown notes into the upload area. Review your
   selection, then choose **Upload documents**. Use recognizable filenames:
   uploads retain filenames as paper titles. Up to 10 files per batch, 25 MiB per
   file, and 100 pages per PDF. PDFs must be unencrypted and contain selectable
   text; apply OCR to scanned papers first.
5. Follow **Processing activity** until the papers are ready, then choose
   **Search your papers**. Your paper library lists uploaded files and their
   status; **Open original** opens a ready source in a new tab.
6. Ask a specific question about a method, finding, or limitation. Question
   starters fill the question field so you can edit it before searching. Search
   results are passages from your collection, not generated answers.
7. Inspect a result and shortlist useful passages. Open **More evidence options**
   to review and export the shortlist, including its source snapshot. The
   shortlist is temporary for the current session; export it before leaving.

Open **Research guide** in the sidebar any time for this workflow, PDF advice,
privacy details, and keyboard shortcuts. **Ctrl/⌘ K** opens quick actions;
**Ctrl/⌘ Enter** submits a question; **Escape** closes an inspector or dialog.

## Optional cited answers

Passage search works without a language model server or paid API. The default
installation does not configure an answer provider. To generate cited answers,
follow [generation setup](OPERATIONS.md#optional-generation), then choose
**Answer** in Ask. Cloud providers require explicit consent for each collection.
Local generation in Docker must share the worker's network namespace; the host's
loopback address does not refer to the worker container.

Generated answers appear in **Saved research**, where you can revisit the question,
source snapshot, model, and citations. Export Markdown, BibTeX, JSON, or CSV from
the saved run. Always verify the original paper before using a claim. Retrieval
scores describe ranking, not scientific validity.

## Stop, resume, and diagnose

| Task | Windows PowerShell | macOS/Linux |
|---|---|---|
| Check prerequisites | `.\start.ps1 doctor` | `sh start.sh doctor` |
| See service status | `.\start.ps1 status` | `sh start.sh status` |
| Read recent logs | `.\start.ps1 logs` | `sh start.sh logs` |
| Stop while keeping data | `.\start.ps1 stop` | `sh start.sh stop` |
| Resume | `.\start.ps1` | `sh start.sh` |

Direct Docker equivalents are `docker compose ps -a`,
`docker compose logs --tail=100 workspace identity postgres init`, and
`docker compose down`. Stopping preserves your papers, account, database, and
model cache. **Do not add `--volumes` to `down` unless you intend to delete them.**

| Symptom | Recovery |
|---|---|
| Docker is not running | Start Docker Desktop/Engine, wait for it to be ready, then retry. Windows must use Linux containers. |
| `include` or `--wait` is unknown | Update Docker Desktop or the Compose plugin to Compose 2.20 or newer. |
| A port is already allocated | Stop the process using 8000/8080 and retry. The local OIDC URLs use these exact ports; changing only a port mapping breaks sign-in. |
| Startup timed out | Read logs. The first model download can be slow or interrupted. Retry the same start command after restoring the connection. |
| PowerShell blocks the script | Use the direct `docker compose up --build --wait --wait-timeout 900` command from the repository root. No execution-policy change is required. |
| Sign-in redirects fail | Use `http://127.0.0.1:8000` throughout. Do not alternate with `localhost`. Check identity status and logs. |
| Upload fails | Open Processing activity for the reason. Check file limits, readable PDF text, encryption, and worker status. Failed uploads appear in the paper library and are not searchable. |
| Answer is unavailable | Use Find passages. Generated answers need a separately configured provider. |

The default stack keeps the existing `retrievec-demo` project and volume names.
If you used `compose.demo.yaml` before, your data is reused by the new default
stack. The old explicit `-f compose.demo.yaml --profile demo` command still works.
Native developers who previously used the default stack only for PostgreSQL
should now use `docker compose -f compose.database.yaml up -d postgres`; this
preserves the original database-only volume naming for the same checkout.

For backups, native development, deployment, identity, and service configuration,
see [operations](OPERATIONS.md). For UI behavior and its scope, see
[the paper workspace design notes](design/PAPER_WORKSPACE.md).
