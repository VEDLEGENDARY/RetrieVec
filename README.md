# RetrieVec

A local retrieval engine and reproducible experiment workbench for research papers.
The project specification calls this architecture **RetrievalLab**; this repository
is RetrieVec, and the Python package keeps the name `retrievallab`.

**Current scope: step 1, workspace scaffold.** The entry points support help and
version output. Corpus processing, search, HTTP serving, and evaluation are not
implemented yet. See [implementation status](docs/IMPLEMENTATION_STATUS.md).

## Setup

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

Runtime dependencies are currently empty. Development and build dependencies
are pinned in `python/requirements-dev.txt` and `python/pyproject.toml`.
Update the pins together and validate on both CI platforms.

Read the [architecture overview](docs/architecture/overview.md) and
[contribution workflow](CONTRIBUTING.md) before implementing the next step.
