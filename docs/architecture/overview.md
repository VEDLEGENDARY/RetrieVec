# Architecture overview

Retrieval Lab implements the Retrieval Lab plan: a versioned retrieval engine and an
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

Python packages are `corpus`, `client`, and `evaluation`. Corpus preparation now
provides deterministic snapshots and local text/PDF import using the Go analyzer.
The client calls the live service and captures versioned runs; evaluation replays
saved results with explicit draft/reviewed judgment handling.

## Weeks 3–4 implementation

The shared Go index.Reader boundary supports the memory reference and immutable
multi-segment disk readers. The segment reader validates once, then decodes
requested posting lists with bounded reads. Global statistics and external-ID
ordering preserve ranking and phrase semantics across segment boundaries.

PostgreSQL owns collection authorization, ready snapshots, the active-pointer CAS,
and fenced ingestion leases. The worker publishes immutable artifacts, registers
and prepares them, validates declared capabilities, then activates transactionally.
Go's authenticated generated RPC independently checks collection ownership.
Python pins one retrieval snapshot across RPC, embedding vectors and passages.
Exact cosine search and RRF preserve separate sparse/dense/fused score fields.

Relevant contracts: [segments](../contracts/segment-format-v1.md),
[ingestion](../contracts/ingestion-v1.md), [hybrid](../contracts/hybrid-v1.md),
and [evaluation](../contracts/evaluation-v1.md).
Setup and reproduction: [week 4 handoff](../reports/week-04-baseline.md).
Human-reviewed relevance and broader real-corpus evidence remain explicit gates.

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
