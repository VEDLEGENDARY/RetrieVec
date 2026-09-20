# 🔬 RetrieVec

> A local retrieval engine and reproducible experiment workbench for research papers.

[![Go Version](https://img.shields.io/badge/Go-1.26.8-00ADD8?style=flat&logo=go)](https://go.dev/dl/)
[![Python Version](https://img.shields.io/badge/Python-3.13.15-3776AB?style=flat&logo=python)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)](#setup)
[![Status](https://img.shields.io/badge/Status-In%20Development-orange)](docs/IMPLEMENTATION_STATUS.md)

**RetrieVec** (`retrievec`) is a zero-cloud, fully offline workbench designed for deterministic paper processing, positional indexing, full-text BM25 search, Boolean/phrase search, and reproducible experiment evaluation.

---

## ✨ Key Features

* **🔒 Deterministic Ingestion:** Offline text and PDF extraction with hash-verified snapshot manifests.
* **⚡ Pure Go Search Engine:** Custom positional indexing, BM25 scoring, and Boolean/phrase query engine.
* **🧪 Experiment Workbench:** Built-in run capture via HTTP endpoints and Python CLI for reproducible evaluations.
* **📦 Fully Self-Contained:** Zero cloud accounts, databases, GPUs, or external search dependencies required.

---

## 🛠️ Technical Stack & Dependencies

| Component | Stack | Version / Notes |
| :--- | :--- | :--- |
| **Search Engine** | [Go](https://go.dev/dl/) | **`1.26.8`** (Uses Go standard library only) |
| **Tooling & CLI** | [Python](https://www.python.org/downloads/) | **`3.13.15`** (PDF extractor is sole runtime dep) |
| **Platforms** | Windows & Linux | CI pins dependencies and runs cross-platform |

> [!IMPORTANT]
> Dependencies are strictly pinned in `python/requirements-dev.txt` and `python/pyproject.toml`. Updates must be committed together and validated across both Windows and Linux CI platforms.

---

## 🚀 Setup & Installation

Ensure [Go 1.26.8](https://go.dev/dl/) and [Python 3.13.15](https://www.python.org/downloads/) are installed and Go's `bin` directory is added to your system `PATH`.

Select your platform below to set up the environment and run developer checks:

### PowerShell (Windows)

```powershell
# Create and activate virtual environment
py -3.13 -m venv .venv

# Install dependencies in editable mode
.\.venv\Scripts\python.exe -m pip install -r python/requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e ./python

# Run developer verification suite
.\.venv\Scripts\python.exe scripts/check.py
.\.venv\Scripts\retrievec.exe --version

# Verify Go engine build
Push-Location engine
go run ./cmd/retrievald --version
Pop-Location
```

### Bash (Linux)

```bash
# Create virtual environment
python3.13 -m venv .venv

# Install dependencies in editable mode
.venv/bin/python -m pip install -r python/requirements-dev.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps -e ./python

# Run developer verification suite with race detector (requires GCC/C compiler)
.venv/bin/python scripts/check.py --race
.venv/bin/retrievec --version

# Verify Go engine build
(cd engine && go run ./cmd/retrievald --version)
```

> [!NOTE]
> * Neither shell requires activating the virtual environment; direct executable paths are used.
> * Package installation requires network access; all subsequent checks and workflows use local synthetic fixtures completely offline.

---

## ⚡ Quick Start: Engine Daemon & Run Capture

### 1. Launch the Engine Daemon

Once built, start the retrieval server targeting a snapshot directory:

```bash
# Windows
artifacts/bin/retrievald.exe --corpus <snapshot-directory>

# Linux
artifacts/bin/retrievald --corpus <snapshot-directory>
```

### 2. Execute Query Benchmark

In a separate terminal, trigger a query run and capture results:

```bash
# Windows
.\.venv\Scripts\python.exe -m retrievec run --queries datasets/fixtures/queries-v1.jsonl --output artifacts/runs/example_01

# Linux
.venv/bin/python -m retrievec run --queries datasets/fixtures/queries-v1.jsonl --output artifacts/runs/example_01
```

> [!TIP]
> Always supply a new output directory path for every run. Note that `datasets/fixtures/queries-v1.jsonl` contains one intentional syntax error to test parser resilience.

---

## 🧪 Local Corpus Workflow

Follow these steps to import local research papers and inspect the generated positional index.

### Step 1: Set Engine Location

Build the engine via `scripts/check.py`, then export its executable path:

* **PowerShell:**
  ```powershell
  $env:RETRIEVEC_ENGINE = (Resolve-Path artifacts/bin/retrievald.exe).Path
  ```
* **Linux:**
  ```bash
  export RETRIEVEC_ENGINE=$(realpath artifacts/bin/retrievald)
  ```

### Step 2: Import & Validate Corpus Snapshot

1. Download the **five seed PDFs** defined in `datasets/manifests/seed-papers-v1.json` to `artifacts/papers/` (or supply a custom local manifest).
2. Execute the offline import pipeline and validate the corpus snapshot:

* **PowerShell:**
  ```powershell
  .\.venv\Scripts\python.exe -m retrievec import --manifest datasets/manifests/seed-papers-v1.json --source-root artifacts/papers --output artifacts/snapshots
  .\.venv\Scripts\python.exe -m retrievec validate-snapshot artifacts/snapshots/<snapshot-id>
  ```
* **Linux:**
  ```bash
  .venv/bin/python -m retrievec import --manifest datasets/manifests/seed-papers-v1.json --source-root artifacts/papers --output artifacts/snapshots
  .venv/bin/python -m retrievec validate-snapshot artifacts/snapshots/<snapshot-id>
  ```

### Step 3: Inspect Index & Collection Metrics

To rebuild and inspect the deterministic positional index for a snapshot:

```bash
# Windows
artifacts\bin\retrievald.exe inspect --corpus artifacts\snapshots\<snapshot-id>

# Linux
artifacts/bin/retrievald inspect --corpus artifacts/snapshots/<snapshot-id>
```

The inspect tool reports key corpus metrics:
* Snapshot & Collection metadata
* Term & Vocabulary counts
* Chunking & Tokenization totals
* Average document length ($DL_{avg}$)

*(Note: The positional index is rebuilt in memory at engine startup and is not currently persisted to disk).*

---

## 📁 Repository Structure

```
retrievec/
├── 📁 engine/        # Go retrieval service, search logic, and cmd/retrievald entry point
├── 📁 python/        # Installable corpus, client CLI, and evaluation tooling
├── 📁 datasets/      # Committed synthetic fixtures, manifests, and golden records
├── 📁 docs/          # Architecture decisions, contract specs, and progress status
├── 📁 scripts/       # Cross-platform developer check and validation scripts
└── 📁 artifacts/     # Ignored build binaries, corpus snapshots, and experiment runs
```

---

## 🧹 Code Quality & Formatting Guidelines

The shared `scripts/check.py` script automatically enforces:
* **Go:** `gofmt`, `go vet`, unit tests, and executable builds.
* **Python:** Dependency consistency, `ruff` linting and formatting, and CLI integration tests.

To fix formatting issues prior to submitting changes:

```bash
# Fix Go formatting
gofmt -w engine/

# Fix Python formatting (Windows)
.\.venv\Scripts\python.exe -m ruff format --config python/pyproject.toml python scripts

# Fix Python formatting (Linux)
.venv/bin/python -m ruff format --config python/pyproject.toml python scripts
```

---

## 📚 Documentation & Specifications

Before implementing new features, review the design documents and specifications:

* 📐 **[Architecture Overview](docs/architecture/overview.md)** — High-level system design and design choices.
* 📋 **[Implementation Status](docs/IMPLEMENTATION_STATUS.md)** — Feature roadmap and step completion status.
* 🌐 **[HTTP API Contract](docs/contracts/http-v1.md)** — Go engine REST endpoint specifications.
* 📥 **[Import Contract](docs/contracts/import-v1.md)** — Snapshot generation and hash validation protocol.
* 📊 **[Run Capture Contract](docs/contracts/run-capture-v1.md)** — Format for benchmark run artifacts.
* 🔬 **[Seed Import Report](docs/reports/seed-import-v1.md)** — Baseline reproduction metrics and verification logs.
* 🤝 **[Contribution Workflow](CONTRIBUTING.md)** — Development standards and pull request guidelines.
* 🧪 **[Research Workspace Setup](docs/workspace-setup.md)** — OIDC, uploads, saved cited answers, model configuration, and exports.
* 📝 **[Week 6 Handoff](docs/reports/week-06-workspace.md)** — Actual checks, model results, pending human review, and follow-up work.
