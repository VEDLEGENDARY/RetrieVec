# Retrieval Lab

A local retrieval engine and reproducible experiment workbench for research papers.
The project name is Retrieval Lab. Package and file names use `retrievallab`.

The workspace supports validated corpus snapshots, deterministic text/PDF import,
positional indexing, BM25, Boolean/phrase search, local HTTP and Python run capture.
Reviewed evaluation arrives in later steps. See
[implementation status](docs/IMPLEMENTATION_STATUS.md).

## Setup

After setup, start `artifacts/bin/retrievald.exe --corpus <snapshot-directory>`.
In another terminal run `.venv/Scripts/python.exe -m retrievallab run --queries datasets/fixtures/queries-v1.jsonl --output artifacts/runs/example`.
Use a new output directory each time. The query fixture includes one intentional
syntax error. On Linux omit .exe and use .venv/bin/python.
See [HTTP](docs/contracts/http-v1.md) and [run capture](docs/contracts/run-capture-v1.md).

Install [Go 1.26.8](https://go.dev/dl/) and
[Python 3.13.15](https://www.python.org/downloads/).
CI pins these versions and runs on Windows and Linux. Add Go's `bin` directory to PATH.
No cloud account, database, GPU, or corpus download is needed.

From the repository root in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r python/requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e ./python
.\.venv\Scripts\python.exe scripts/check.py
.\.venv\Scripts\retrievallab.exe --version
Push-Location engine
go run ./cmd/retrievald --version
Pop-Location
```

From the repository root on Linux:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r python/requirements-dev.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps -e ./python
.venv/bin/python scripts/check.py --race
.venv/bin/retrievallab --version
(cd engine && go run ./cmd/retrievald --version)
```

Linux race checks require a C compiler such as GCC. Windows local checks omit the
race detector by default; Linux CI always enables it. Neither shell requires
virtual-environment activation. Installations need network access; the checks
use local code and synthetic fixtures only.

The shared check script enforces Go formatting, vet, tests, and executable build,
then Python dependency consistency, Ruff lint/format, and installed CLI tests.
Fix formatting with `gofmt -w <file>` and
`.venv\Scripts\python.exe -m ruff format --config python/pyproject.toml python scripts`
(use `.venv/bin/python` on Linux).

## Layout

| Directory | Responsibility |
| --- | --- |
| `engine/` | Go service entry point and retrieval packages |
| `python/` | Installable corpus, client, and evaluation tooling |
| `datasets/` | Committed synthetic fixtures, manifests, and evaluation records |
| `docs/` | Architecture decisions, contracts, reports, and implementation status |
| `scripts/` | Cross-platform developer checks |
| `artifacts/` | Ignored generated binaries, snapshots, and experiment outputs |

The PDF extractor is the only Python runtime dependency; Go uses its standard library.
Dependencies are pinned in `python/requirements-dev.txt` and `python/pyproject.toml`.
Update the pins together and validate on both CI platforms.

Read the [architecture overview](docs/architecture/overview.md) and
[contribution workflow](CONTRIBUTING.md) before implementing the next step.

## Local corpus workflow

Build the engine through scripts/check.py, then set its path in PowerShell:

```powershell
$env:RETRIEVALLAB_ENGINE = (Resolve-Path artifacts/bin/retrievald.exe).Path
.\.venv\Scripts\python.exe -m retrievallab import --manifest datasets/manifests/seed-papers-v1.json --source-root artifacts/papers --output artifacts/snapshots
.\.venv\Scripts\python.exe -m retrievallab validate-snapshot artifacts/snapshots/<snapshot-id>
```

On Linux use .venv/bin/python and set RETRIEVALLAB_ENGINE to the absolute path of
artifacts/bin/retrievald. Download the five PDFs identified by the seed manifest
to artifacts/papers first, or supply your own local source manifest. Import is
offline and verifies pinned source hashes. See the [import contract](docs/contracts/import-v1.md)
and [seed inspection report](docs/reports/seed-import-v1.md) for reproduction details.

To inspect a validated corpus after building the engine:

```powershell
artifacts\bin\retrievald.exe inspect --corpus artifacts\snapshots\<snapshot-id>
```

The command rebuilds the deterministic positional index and reports its snapshot,
collection, term, chunk, token, and average-length statistics. The index is rebuilt
at startup and is not yet persisted to disk.
