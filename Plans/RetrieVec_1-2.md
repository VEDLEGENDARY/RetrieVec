# RetrievalLab: Project Specification and Weeks 1–2 Plan

## Required engineering workflow

Read and follow [ENGINEERING_WORKFLOW.md](ENGINEERING_WORKFLOW.md) in full before changing the repository. Its approval boundaries are part of this handoff.

- Work on only the first incomplete commit-sized step.
- Obtain approval for the proposed branch before creating or switching to it.
- Never implement or commit directly on `main`/`master`; integrate only through an approved pull request.
- After implementation and validation, present the diff, checks, limitations, and exact message; obtain approval before committing.
- Obtain separate authorization before pushing, opening/updating a pull request, merging, or starting the next step unless that exact action is already authorized.
- Use natural, project-focused branch names, commit messages, code, comments, documentation, and PR descriptions. Do not add tool attribution or fabricated authorship/review.
- Preserve unrelated changes and record actual evidence and incomplete gates honestly.
## Project

Build a versioned retrieval engine and experiment platform, demonstrated through a research workbench for RAG and ML papers.

Users will select a paper collection, compare retrieval methods, inspect supporting passages, generate cited research comparisons, and save reproducible experiments. Published findings and results measured by RetrievalLab must remain distinguishable.

The technical focus is custom retrieval infrastructure, reproducibility, evaluation, and reliability. AskUTD is a separate club project; a future integration must not become a delivery dependency.

## Constraints

- Development: 2–3 hours daily; approximately eight weeks for the initial release.
- Hardware: Core Ultra 7 155H, integrated Arc graphics, 16 GB shared system RAM, 1 TB SSD.
- Core development must run locally. Colab and student cloud credits are available for later experiments.
- Private repository during development; public release after owner approval.
- Use this dedicated RetrieVec repository, not an unrelated portfolio workspace.
- Follow issues → feature branches → PRs → CI → reviewed merge. Record major architecture decisions and actual benchmark results.

## Architecture and roadmap

| Component | Responsibility |
|---|---|
| Go retrieval service | Positional index, BM25, Boolean/phrase search; later persistence and optimization |
| Python tooling/API | Corpus processing, evaluation, model integration, orchestration |
| TypeScript interface | Research workspace, comparisons, source inspection, experiments |
| PostgreSQL | Later user, collection, ingestion, and experiment metadata |
| Artifact storage | Source files, corpus snapshots, indexes, vectors, run outputs |

| Milestone | Deliverables |
|---|---|
| Weeks 1–2 | Corpus pipeline, correct Go sparse search, HTTP API, Python evaluation, baseline report |
| Weeks 3–4 | Persistent snapshots, recoverable ingestion, exact dense search, hybrid fusion |
| Weeks 5–6 | Interface, authentication, private collections, cited synthesis |
| Weeks 7–8 | Failure testing, profiling, reproducibility report, demonstration |
| Later | OCR, tables/equations, evaluated chart interpretation, reranker training, index optimizations |

Long-term requirements: private per-user collections, saved conversations/experiments, source-page evidence, Markdown/BibTeX/JSON/CSV exports, and explicit cloud-processing preferences. Enforce authorization before retrieval and across citations, caches, and exports.

Use established authentication, extraction, and model libraries. Implement retrieval algorithms yourself. Evaluate approximate vector indexing against exact search before selecting a custom approach.

## Weeks 1–2 scope

Deliver a local corpus-to-search-to-evaluation workflow. The index is immutable in memory and rebuilt at startup; corpus snapshots are stored on disk.

Required:

1. Repository, CI, setup instructions, and architecture decisions.
2. Validated, deterministic corpus snapshots with provenance.
3. Custom positional index, BM25, Boolean/phrase search.
4. Go HTTP service and Python client.
5. Reviewed evaluation seed, reproducible runs, baseline measurements.
6. Demonstration commands and next-milestone backlog.

Defer dense retrieval, LLM synthesis, production authentication, PostgreSQL integration, frontend, OCR, training, persistent index segments, and cloud hosting.

## Repository structure

```text
engine/
  cmd/retrievald/
  internal/{analysis,corpus,index,query,scoring,search,httpapi}/
python/
  src/retrievallab/{corpus,client,evaluation}/
  tests/
datasets/{fixtures,manifests,evaluation}/
docs/
  architecture/
  contracts/
  reports/
  IMPLEMENTATION_STATUS.md
scripts/
artifacts/                 # ignored generated data
.github/workflows/
```

Commit synthetic fixtures, source manifests, and concise reports. Exclude private papers, credentials, downloaded PDFs, generated indexes, and large artifacts. Pin dependencies and use Windows-compatible development commands.

## Corpus specification

Start with 10–20 synthetic correctness documents and 5–10 real text-based papers. Expand toward 30–50 papers by week two; later target 200–500. Cover lexical/dense retrieval, fusion, reranking, chunking, and evaluation.

Support local imports first. Record source/version/license information; verify source access rules before automated downloads and redistribution rights before committing full text.

Use versioned UTF-8 JSONL:

| Record | Required fields |
|---|---|
| Paper | `paper_id`, `paper_version_id`, title, authors, source URL or null, source SHA-256, extraction version, license note |
| Chunk | `chunk_id`, paper/version IDs, collection ID, ordinal, text, text SHA-256, chunker version, page range or null |
| Manifest | Schema version, file hashes, source records, extraction/chunker versions, counts, snapshot ID |

Derive chunk IDs from paper version, extraction/chunker versions, ordinal, and text hash. Hash canonically ordered content; exclude timestamps from snapshot identity.

Validate duplicate IDs, missing references, invalid encoding, empty chunks, unknown schema versions, and hash mismatches. Stage outputs and publish only after validation.

Chunker v1: paragraph-aware packing, configurable 256-token starting budget, deterministic splitting of oversized paragraphs, no overlap. Preserve original text and available page provenance; never invent page locations. Version every behavioral change.

Acceptance: identical inputs/configuration produce the same snapshot identity; changed content/configuration changes it.

## Analyzer and index

Rank chunks, returning their paper identities. Paper grouping is a separate operation.

Analyzer v1:

- Unicode lowercase; tokens are maximal runs of letters or digits.
- Punctuation separates tokens; retain stopwords.
- No stemming or implicit Unicode normalization.
- Zero-based token positions within each chunk.
- Shared Go/Python fixtures; use the Go analyzer during preparation if exact parity is otherwise uncertain.

Examples: `RAG-based` → `rag`, `based`; `BM25` → `bm25`; `don't` → `don`, `t`.

Index layout:

```text
map[token][]Posting
Posting { internal_chunk_id, term_frequency, positions[] }
chunk_lengths[]
chunk_metadata[]
external_id_to_internal_id
chunk_count, average_chunk_length
```

Build in external-ID order. Posting IDs and positions strictly increase; each term/chunk pair occurs once; frequency equals position count. Reject zero-token chunks. Document frequency equals posting-list length. Search must not mutate the index.

## Ranking and query semantics

BM25, with `N` indexed chunks:

```text
idf(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
score(d,q) = sum over unique positive query terms t of:
  idf(t) * tf(t,d) * (k1 + 1) /
  (tf(t,d) + k1 * (1 - b + b * length(d) / avg_length))
```

Defaults: `k1=1.2`, `b=0.75`; require finite values, `k1>0`, `0<=b<=1`. Repeated query terms do not add weight. Sum contributions in deterministic term order. Sort descending by score, then ascending external chunk ID. Start with full sorting; optimize top-k only after equivalence tests.

Two explicit modes:

- `free_text`: OR candidates across analyzed terms, ranked by BM25.
- `structured`: evaluate constraints, then rank surviving chunks by unique positive terms. No phrase boosts or query expansion.

```text
expression := or_expr
or_expr    := and_expr (OR and_expr)*
and_expr   := unary_expr (AND unary_expr)*
unary_expr := NOT unary_expr | primary
primary    := TERM | PHRASE | '(' expression ')'
```

Use a lexer and recursive-descent AST parser. Uppercase operators; explicit operators between operands; precedence `NOT > AND > OR`. Bare terms must analyze to one token. Phrases match consecutive positions within one chunk; support escaped quotes/backslashes.

Negation is relative to the loaded collection. Positive scoring terms are those under an even number of `NOT` nodes; reject expressions with no positive terms. Include nested negation and zero-score matches in tests.

Reject malformed syntax, empty phrases, invalid escapes, and empty analyzed queries. Initial limits: 4,096 characters, 256 parser tokens, 32 nesting levels, `top_k` 1–100. Bound analyzed phrase length as well as parser token count.

## HTTP and Python contracts

```text
retrievald --corpus <snapshot-directory> --listen 127.0.0.1:8091
```

Validate/load/build before readiness. Bind locally; support graceful shutdown, request/body limits, and timeouts.

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Liveness |
| `GET /readyz` | Readiness and snapshot ID |
| `GET /v1/stats` | Versions, chunk/term counts, average length |
| `POST /v1/search` | Ranked retrieval |

```json
{
  "query": "\"dense retrieval\" AND NOT vision",
  "mode": "structured",
  "top_k": 10,
  "explain": false
}
```

Response includes request/snapshot/analyzer IDs, retrieval configuration, total matches, timings, and hits containing rank, chunk/paper/version IDs, title, score, text, and nullable page range. Optional explanations use actual term contributions. Prohibit non-finite scores.

Errors use `{code, message, position?}`: 400 invalid input, 413 oversized body, 405 unsupported method, 503 not ready, 500 unexpected failure. Keep stack traces out of responses.

Python must call the real service, validate responses, capture errors, and write evaluation artifacts. A second proxy API is unnecessary in this milestone.

## Evaluation and benchmarks

Separate algorithm correctness, retrieval usefulness, and operational performance.

Target 20 owner-reviewed questions with a frozen development/held-out split, such as 12/8. Include term lookup, vocabulary mismatch, comparisons, structured constraints, and out-of-corpus probes. Generated questions/judgments remain drafts until reviewed.

Grades: 0 irrelevant; 1 related background; 2 useful evidence; 3 particularly complete evidence. Grades 2–3 count as binary relevant. Store query/chunk IDs, grade, reviewer, review status, rationale, and dataset/snapshot versions. Keep unjudged distinct from irrelevant.

Pool candidates from BM25, a simple lexical baseline, and manual inspection where practical. Report incomplete judgments and pooling bias.

Metrics:

- nDCG@10 using `2^grade - 1` gain.
- MRR@10 and recall@10 over known judged positives.
- Judgment coverage@10 and empty-result rate.
- Report undefined/no-positive cases separately; state treatment of unjudged hits.

Run outputs:

```text
manifest.json  # commit + dirty state, versions, hashes, config, environment
results.jsonl  # exact queries, ranked IDs/scores, timings, errors
metrics.json   # per-query and aggregate values, conventions
report.md      # findings, limitations, reproduction commands
```

Record CPU/RAM/OS, Go/Python versions, corpus size, warmups, measured request count, and concurrency. Measure build time, serial and bounded-concurrent p50/p95 latency, and memory when reliable. Distinguish server timing from round-trip latency. Synthetic scale tests do not establish real-corpus quality.

Identical inputs must reproduce rankings/scores; timings may vary. Metrics must be recomputable from saved results. Use held-out results after development decisions are frozen; record later reuse.

## Tests and CI

- Corpus validation, hash determinism, and chunking fixtures.
- Analyzer parity and posting/position invariants.
- Hand-calculated BM25 cases, numeric tolerance, tie ordering, repeated terms.
- Parser precedence/errors/limits and bounded fuzz tests.
- Boolean/phrase results compared with a simple independent reference evaluator.
- Metric tests with hand-computed rankings, missing judgments, and no-positive cases.
- HTTP errors, concurrent reads, Python-to-Go integration.
- Go race checks on a supported platform, formatting/static checks, Python lint/tests.

CI uses committed synthetic fixtures without cloud services or paper downloads. Keep noisy performance thresholds out of ordinary correctness gates.

## Weeks 1–2: 14 commit-sized steps

Each step adds one coherent capability and ends with a separate commit containing its implementation, tests, and relevant documentation. Execute in order; steps are not fixed calendar days. Keep all 14 milestone commits visible when merging PRs; do not squash the entire milestone into one commit. Group related steps into focused PRs where useful.

| Step | Commit message | Deliverable | Validation before commit |
|---|---|---|---|
| 1 | `chore: scaffold Go and Python workspace with CI` | Packages, entry points, ignore rules, architecture overview, CI | Both language checks run locally and in CI |
| 2 | `feat: add validated deterministic corpus snapshots` | Record schemas, IDs, hashes, manifests, synthetic fixtures | Determinism, duplicate/reference/hash rejection tests |
| 3 | `feat: add versioned analyzer and token fixtures` | Go analyzer and preparation interface/parity contract | Unicode, punctuation, empty input, and position fixtures |
| 4 | `feat: import and chunk text-based papers` | Local importer, deterministic paragraph chunker, provenance | Seed snapshot validates; chunk boundaries/pages inspected |
| 5 | `feat: build positional inverted index` | Sorted postings, chunk lookup, collection statistics | Exact postings, positions, frequencies, and invariants |
| 6 | `feat: rank free-text queries with BM25` | Formula, OR candidates, stable ranking, explanations | Independent score fixtures, parameter errors, deterministic ties |
| 7 | `feat: parse structured retrieval queries` | Lexer, AST, precedence, escapes, limits | Valid ASTs, malformed queries, nesting and size limits |
| 8 | `feat: execute Boolean and phrase search` | Set operations, positional phrases, scoped negation, scoring | Reference evaluator parity, repeated-token phrases, nested NOT |
| 9 | `feat: expose sparse search over HTTP` | Search/health/readiness/stats, limits, shutdown | Real HTTP success/error tests and concurrent reads |
| 10 | `feat: add Python retrieval client and run capture` | Service client, query-file CLI, versioned result manifests | Live Go integration, error capture, repeated-run equality |
| 11 | `feat: add reviewed retrieval evaluation dataset` | Expanded corpus manifest, question splits, labeling guide, reviewed judgments | IDs resolve; review states, hashes, and held-out split verified |
| 12 | `feat: compute retrieval metrics and baseline reports` | Metric runner, per-query results, readable report | Hand-computed metric fixtures; saved results reproduce metrics |
| 13 | `test: add fuzz concurrency and performance harnesses` | Bounded fuzzing, race checks, repeatable benchmark workloads | No unresolved correctness failures; environment/timings recorded |
| 14 | `docs: add reproducible demo and milestone handoff` | Tested setup/demo commands, findings, acceptance status, next backlog | Clean-checkout rehearsal and final acceptance review |

Step 11 requires actual owner review; draft labels may be prepared earlier while independent work continues. Do not mark the reviewed dataset complete until review occurs. Additional corrective commits are appropriate when needed; the 14 steps describe logical additions, not a restriction on fixing defects. Update `docs/IMPLEMENTATION_STATUS.md` with each step's commit ID and validation evidence.

Keep owner review within the time budget and request small labeling batches early. If work exceeds two weeks, extend the milestone or reduce corpus breadth; retain correctness gates.

## Final acceptance

- Clean checkout runs locally using documented commands.
- Corpus, analyzer, index, scoring, parser, and metrics pass independent correctness checks.
- Go service and Python runner work together with deterministic rankings.
- Concurrency checks pass; malformed input produces safe errors.
- Reviewed evaluation results include coverage, environment, limitations, and reproduction steps.
- CI passes; meaningful changes are organized into reviewable PRs.
- `docs/IMPLEMENTATION_STATUS.md` identifies completed gates, results, open issues, and next actions.

Demo: build snapshot → start service → free-text search with explanations → phrase/Boolean search → invalid-query error → evaluation report → repeatable rankings → known failure case.

## Next milestone

Persistent checksummed index segments, atomic snapshot activation, recoverable/idempotent ingestion, PostgreSQL ownership metadata, exact dense retrieval, RRF fusion, and expanded relevance pools. RRF accumulates contributions per candidate before top-k selection.

For each optimization, record the baseline, hypothesis, correctness check, measured result, and retention decision.

## Later architecture: segment format v1

Implement with persistent indexes after weeks 1–2. Store this contract in `docs/contracts/segment-format-v1.md` alongside golden binary fixtures. It defines the first format, not an already implemented capability.

```text
[96-byte Header | Chunk Table | Term Dictionary | Delta-Encoded Postings | SHA-256 Footer]
```

Fixed-width integers are unsigned little-endian. Variable integers use canonical unsigned base-128 varints (ULEB128), bounded to 64 bits. Offsets are absolute file-byte offsets; blocks are contiguous with no padding.

| Header byte offset | Type | Value |
|---|---|---|
| 0 | 8 bytes | ASCII `RLSEG001` |
| 8 | u16 | Format version: 1 |
| 10 | u16 | Flags: 0; reject unknown flags |
| 12 | u32 | Header size: 96 |
| 16 | u64 | Total file size, including footer |
| 24 | u64 | Chunk count |
| 32 | u64 | Term count |
| 40 | u64 | Chunk-table offset: 96 |
| 48 | u64 | Dictionary offset |
| 56 | u64 | Postings offset |
| 64 | u64 | Footer offset |
| 72 | u64 | Total analyzed token count |
| 80 | 16 bytes | Reserved: all zero |

Block encodings:

- **Chunk table:** exactly `chunk_count` records sorted by external chunk ID bytes. Each is `[ID byte length: varint | UTF-8 ID | token length: varint]`. Record ordinal is the zero-based segment-local chunk ID. Paper metadata/text remain in the referenced corpus snapshot.
- **Term dictionary:** exactly `term_count` records sorted by UTF-8 term bytes: `[term byte length: varint | term bytes | df: varint | postings absolute offset: u64 | postings byte length: u64]`. Load a lookup table at startup; no prefix compression in v1.
- **Postings:** one contiguous stream per dictionary term, in dictionary order, containing exactly `df` records: `[chunk gap: varint | tf: varint | tf position gaps: varints]`. First chunk/position values are absolute zero-based values; later values are positive deltas. Position encoding restarts for each chunk. `tf` must be positive.
- **Footer:** 32-byte SHA-256 digest of every preceding byte. This detects corruption; it is not authentication.

The snapshot manifest references each segment by full-file SHA-256, corpus snapshot ID, analyzer version, and scoring-statistics version. In v1, segment chunk sets are disjoint; compaction preserves external IDs. Compute BM25 statistics across the snapshot, not independently per segment. Updates/deletions require snapshot replacement until explicitly specified.

Readers validate file size, ordered offsets, bounds without integer overflow, counts, sorted IDs/terms, gaps, positions, token totals, checksum, and exact block consumption before activation. Reject unknown versions, truncation, trailing data, and excessive allocations. Empty segments are not emitted.

Write to a temporary file, flush and validate it, then publish a manifest referencing immutable segments. Specify and test platform-specific flush/rename behavior before claiming crash durability. Existing queries retain their snapshot until completion.

Acceptance: golden-byte tests, round-trip ranking equivalence with the in-memory baseline, malformed-file fuzzing, checksum failures, compaction equivalence, and interrupted-publication recovery. Benchmark compression ratio, load time, memory, and query latency before adding skip blocks or memory mapping.

## Later architecture: Python–Go RPC

Adopt **gRPC with Protobuf** for the internal boundary after weeks 1–2. Keep the external research API HTTP/JSON; both internal transports initially call the same Go search implementation. Generated contracts and explicit lifecycle handling motivate the choice; measure performance rather than assume gRPC is faster. [gRPC concepts](https://grpc.io/docs/what-is-grpc/core-concepts/)

```text
Client → Python API [authorize, resolve/pin snapshot]
                    → Go Search RPC → sparse candidates
                    → Python dense search / fusion / ML reranking
                    → evidence response
```

Go does not call back into Python. Python owns orchestration and model execution. Keep the reranker in the Python process/worker initially; a separate reranker RPC is unnecessary until independent scaling warrants it.

Store `proto/retrievallab/retrieval/v1/retrieval.proto` with generated Go/Python bindings and pinned generation tools. Initial unary RPCs:

| RPC | Request | Response |
|---|---|---|
| `Search` | Request ID, authorized scope, explicit snapshot ID, query, query-mode enum, candidate limit, explain flag | Snapshot/config IDs, ordered candidates, match count, stage timings |
| `GetSnapshotInfo` | Authorized scope, snapshot ID | Corpus/analyzer versions, counts, availability |

Candidate fields: external chunk ID, paper/version IDs, `double` sparse score, rank, optional bounded term contributions. Python fetches passage text from the same pinned corpus snapshot for reranking. Missing snapshot data fails explicitly; never substitute the latest version. Store sparse, fused, and reranker scores separately with their configuration/model versions.

Contract requirements:

- Python resolves scope from the authenticated user; Go verifies the authenticated service identity and scope/snapshot mapping. An arbitrary client-supplied scope string is not authorization. Include scope and snapshot in cache keys.
- Reuse channels. Require deadlines and propagate cancellation into Go search loops and Python model scheduling; application work must cooperate with cancellation. [Deadlines](https://grpc.io/docs/guides/deadlines/), [cancellation](https://grpc.io/docs/guides/cancellation/).
- Validate limits independently in both services: initially 1–1,000 candidates, 4,096 query characters, and 4 MiB messages. Bound concurrent requests and model batches; return `RESOURCE_EXHAUSTED` under overload.
- Use `INVALID_ARGUMENT`, `PERMISSION_DENIED`, `NOT_FOUND`, `FAILED_PRECONDITION`, `UNAVAILABLE`, and deadline/cancellation statuses consistently. Retry only transient failures for read-only calls against the same snapshot, within the original deadline and a bounded retry budget.
- Bind to loopback for local development; use authenticated encrypted transport across hosts. No public Go endpoint.
- Preserve field numbers/types; reserve deleted field numbers/names. Use an unspecified zero enum value and validate required semantic fields. Commit compatibility checks and cross-language fixtures. [Protobuf evolution](https://protobuf.dev/programming-guides/proto3/).

Acceptance: HTTP/RPC ranking parity, generated-client integration, scope isolation, pinned-snapshot consistency, deadline/cancellation tests, overload behavior, and compatible schema evolution. Benchmark equal workloads over HTTP and gRPC, including payload size, serialization cost, and end-to-end reranking latency. Retire duplicate internal HTTP search only after migration passes; operational health endpoints may remain.

## Implementation task prompt

> Read this handoff completely, then read Plans/ENGINEERING_WORKFLOW.md, prerequisite plans, repository instructions, and implementation status. Follow every approval boundary. Work only on the first incomplete commit-sized step: propose its branch, scope, checks, and commit message, then wait for branch approval before changing code. After approval, implement and validate only that step, present the complete diff and results, and wait for commit approval. Do not work directly on main, push, open or merge a pull request, or begin another step without the required authorization. Keep repository language natural and project-focused, preserve unrelated work, and report actual evidence and incomplete gates.
