# Architecture overview

RetrieVec implements the RetrievalLab plan: a versioned retrieval engine and an
experiment workbench for research papers. Published findings and measurements
produced by the workbench must remain distinguishable.

## Weeks 1–2 boundary

Go owns the custom positional index, query parser, BM25, Boolean/phrase search,
and local HTTP service. Python owns source preparation, deterministic corpus
snapshots, the real HTTP client, and evaluation artifacts. The index is immutable
in memory, loaded and rebuilt from a validated on-disk snapshot at startup.

Go package boundaries:

- `analysis`: versioned tokenization and token positions.
- `corpus`: snapshot records, validation, and loading.
- `index`: postings, chunk metadata, and collection statistics.
- `query`: structured query lexing and parsing.
- `scoring`: BM25 configuration and term contributions.
- `search`: candidate evaluation and deterministic ranked results.
- `httpapi`: bounded requests, errors, health, and readiness.

Python packages are `corpus`, `client`, and `evaluation`. In step 1 these packages
only document their boundaries. No retrieval behavior is claimed by this scaffold.

Data flow planned for the milestone:
local sources → validated corpus snapshot → Go index/service → Python client
→ saved results and recomputable metrics. The HTTP service will bind to loopback.
No proxy API is needed for this milestone.

## Reproducibility and data handling

Snapshot identities derive from canonical content and versioned configuration,
excluding timestamps. Analyzer behavior, source provenance, and retrieval
configuration must be recorded. Later evaluation runs must capture commit/dirty
state, hashes, environment, exact rankings, timings, and judgment conventions.

Commit synthetic fixtures and source manifests. Store generated output separately
and keep private source files and credentials out of version control.
Relevance judgments require owner review; drafts do not count as reviewed data.

## Deferred work

Persistent segment files, gRPC/Protobuf, dense retrieval, fusion, model integration,
frontend, production authentication, PostgreSQL, OCR, and cloud hosting are later
work. The plan's segment and RPC specifications are design inputs, not implemented
contracts. Future authorization must cover retrieval, citations, caches, and exports.
AskUTD integration is independent of delivery.

See [ADR 0001](0001-local-workspace-and-checks.md) for the initial decisions.
