# Architecture overview

RetrieVec implements the RetrieVec plan: a versioned retrieval engine and an
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

## Weeks 5–6 workspace

React uses a same-origin FastAPI service with OIDC/PKCE, opaque database-backed
sessions and CSRF checks. PostgreSQL owns live resource policy, conversations,
run configuration, immutable results, citations, events and expiring exports.
Two independently bounded workers handle ingestion and generation. Go remains
an internal authenticated retrieval service; it checks the asserted principal.

A research request pins the snapshot before enqueueing. The generation worker
retrieves from that identity, packs whole passages against the provider's actual
tokenizer, calls a tool-free model, validates output, rechecks sources and access,
then atomically saves citations/result plus completion. Heartbeats and fencing
prevent cancellation or expired work from publishing a late answer. Inference
never runs inside a database transaction. Interrupted attempts fail explicitly;
replay creates a new run rather than mutating the original.

Local llama.cpp and explicitly consented remote llama.cpp deployments share the
provider interface. Consent binds the collection to the exact configuration
hash. Search does not require generation. See [ADR 0006](0006-grounded-research.md),
the [research contract](../contracts/research-v1.md), and
[week 6 handoff](../reports/week-06-workspace.md).

## Reproducibility and data handling

Snapshot identities derive from canonical content and versioned configuration,
excluding timestamps. Analyzer behavior, source provenance, and retrieval
configuration must be recorded. Later evaluation runs must capture commit/dirty
state, hashes, environment, exact rankings, timings, and judgment conventions.

Commit synthetic fixtures and source manifests. Store generated output separately
and keep private source files and credentials out of version control.
Relevance judgments require owner review; drafts do not count as reviewed data.

## Deferred work

Human-reviewed answer quality, broader real-corpus retrieval evaluation, load
testing, advanced PDF extraction/OCR and public deployment remain future work.
OIDC protocol checks use a signed test issuer; the provided Keycloak setup still
needs a local end-to-end operator smoke test. Structural citation checks alone
cannot establish semantic support or comparative scientific validity.
AskUTD integration is independent of delivery.

See [ADR 0001](0001-local-workspace-and-checks.md) for the initial decisions.
