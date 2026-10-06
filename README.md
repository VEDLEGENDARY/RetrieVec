# RetrieVec

### Your papers. Traceable evidence.

A private research workspace to **find passages, inspect sources, and save cited
answers**—with the question, model and source snapshot kept together.

![Real SciFact demo in RetrieVec](docs/images/workspace.png)

*The local demo searches retained SciFact abstracts. This screenshot shows real
retrieval, not generated answers or a model-quality claim.*

## Try it in 2 minutes

With Docker Desktop running, start the local demo from this checkout:

```sh
docker compose -f compose.demo.yaml --profile demo up --build -d
```

Open **http://127.0.0.1:8000**, choose **Sign in**, then **Register** to create
your local account. The **SciFact starter** collection is already loaded: ask
about “cancer” in **Find passages**, then inspect a result or build a shortlist.

The two-minute path assumes cached images and model files. The first run builds
the app and downloads its pinned MiniLM retrieval model; allow additional time
and an internet connection. Keycloak may need a few seconds after startup.
Ports 8000 and 8080 must be free; use `127.0.0.1` consistently.

The demo includes 24 title/abstract records, no paper PDFs and no generation
provider. It generates credentials into local Docker volumes; no preset password
or cloud consent is included. Create a private collection to upload your papers.

```sh
docker compose -f compose.demo.yaml --profile demo ps
docker compose -f compose.demo.yaml --profile demo down
```

Stopping keeps your volumes and account. For deployment, identity configuration,
backups, tracing, pgvector, Kubernetes, OpenTofu and mTLS, see
[operations](docs/OPERATIONS.md).

## A workspace built around evidence

| Destination | What you can do |
|---|---|
| **Ask** | Switch between cited answers and passage search; inspect what each answer used. |
| **Sources** | Upload text/PDFs, track ingestion, retain source hashes and provenance. |
| **Saved research** | Return to a run, its model and immutable snapshot; export cited results. |

- **Verify before trusting.** Inspect retained passages, source metadata and
  supported PDF highlights. Missing coordinates are explained, never guessed.
- **Compare papers.** Shortlist passages and compare them in a table where
  every data cell cites its source. Export the evidence with its snapshot.
- **Stay in control.** Local generation is optional; cloud providers require
  explicit collection consent. Sign-in, ownership and scope checks protect access.
- **Keep experiments explicit.** Section-aware chunking, reranking, fusion and
  approximate vector search are opt-in. Retrieval scores are not confidence.

Use **Ctrl/⌘ K** for quick actions and **Ctrl/⌘ Enter** to submit either Ask mode.
Keyboard focus, Escape, dark mode and reduced motion are covered by browser tests.

## Measured, with limits

<!-- BEIR RESULTS START -->

| Corpus | Hybrid nDCG@10 | Warm retrieval p50 |
|---|---:|---:|
| SciFact | 0.6670 | 255.35 ms |
| SCIDOCS | 0.1928 | 897.29 ms |

Source: [docs/results/benchmark-2026-10-05-phase3.json](docs/results/benchmark-2026-10-05-phase3.json). Warm local retrieval excludes HTTP, authorization and database work.

<!-- BEIR RESULTS END -->

These are complete BEIR title/abstract corpora and held-out retrieval judgments,
not full-paper answer evaluations. The benchmark's opt-in lossless wordpiece
refinement differs from the product's default PDF upload chunking. No tuning was
performed on test queries. See [protocol, all variants and rejected configurations](BENCHMARKS.md).

The cross-encoder improved SciFact but reduced SCIDOCS quality; it remains opt-in.
Section boundaries did not establish a retrieval improvement. In the local
Qwen2.5 1.5B run, **11 of 60 cases completed; 49 failed**. Those questions are
synthetic and automatic-only; semantic accuracy is unmeasured, human review is
blank, and NLI was **NOT run**. See [answer evaluation](ANSWER_EVAL.md).

## Build and contribute

Go owns retrieval; Python owns ingest, workers and FastAPI; React owns the web
workspace. PostgreSQL holds application state; immutable artifacts retain evidence.

For native development, install Python 3.13, Go 1.26, Node 24 and PostgreSQL 18.
In an activated Python environment:

```sh
python -m pip install -r python/requirements-dev.txt
python -m pip install --no-build-isolation --no-deps -e ./python
python scripts/check.py
cd web
npm ci
npm run build
npm run test:ui -- --workers=2
```

Database integrations require isolated test DSNs; see [verification setup](docs/releases/verification.md).
UI tests use labeled synthetic HTTP fixtures. They complement real-service checks.
Work on focused branches and reviewed PRs; retain separate descriptive commits.
Keep weights, PDFs, credentials and private data outside Git.

| Explore | Link |
|---|---|
| Design and navigation | [Audit](docs/design/AUDIT.md) · [Core flows](docs/design/CORE_FLOWS.md) · [Performance](docs/design/PERF.md) |
| Provenance extensions | [Sections, metadata, PDF locations and comparison](docs/design/PHASE5.md) |
| Architecture | [System architecture](docs/architecture) |
| Release | [Changelog](CHANGELOG.md) · [v0.1.0 candidate](docs/releases/v0.1.0.md) · [Verification](docs/releases/verification.md) |
