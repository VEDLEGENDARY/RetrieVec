# RetrieVec: Weeks 3–4 Handoff

## Required engineering workflow

Read and follow [ENGINEERING_WORKFLOW.md](ENGINEERING_WORKFLOW.md) in full before changing the repository. Its approval boundaries are part of this handoff.

- Work on only the first incomplete commit-sized step.
- Obtain approval for the proposed branch before creating or switching to it.
- Never implement or commit directly on `main`/`master`; integrate only through an approved pull request.
- After implementation and validation, present the diff, checks, limitations, and exact message; obtain approval before committing.
- Obtain separate authorization before pushing, opening/updating a pull request, merging, or starting the next step unless that exact action is already authorized.
- Use natural, project-focused branch names, commit messages, code, comments, documentation, and PR descriptions. Do not add tool attribution or fabricated authorship/review.
- Preserve unrelated changes and record actual evidence and incomplete gates honestly.
## Objective and context

Turn the correct sparse-search baseline into a persistent, recoverable hybrid-retrieval platform. Deliver disk-backed Go segments, consistent snapshots, durable ingestion, Python–Go gRPC, exact dense retrieval, and reproducible sparse/dense/hybrid comparisons.

Read `Plans/RetrieVec_Weeks_1-2.md`, repository instructions, and `docs/IMPLEMENTATION_STATUS.md` first. The earlier plan calls the project RetrievalLab; RetrieVec is the current project/repository name. Preserve existing package names, Protobuf namespaces, and `RLSEG001` file magic unless an explicit migration is necessary. Renaming the product does not require breaking stored formats.

Work in the existing RetrieVec repository. Verify earlier acceptance gates against actual code; fix prerequisite defects before dependent work. Do not assume planned features or reviewed judgments exist.

Constraints: 2–3 hours/day, 16 GB shared system RAM, local CPU operation, optional student cloud resources, private repository. This is an ambitious milestone: preserve correctness and extend the schedule if necessary. It does not include user-facing authentication, frontend, generation, OCR, ANN, or model training.

## Result to demonstrate

Import papers → worker builds immutable sparse and dense artifacts → activate a complete snapshot → query it over Python/Go → compare three retrieval modes → interrupt an ingestion job → recover without changing an in-flight query's snapshot.

## Architecture

```text
Local CLI / internal Python API
  ├─ PostgreSQL: collections, jobs, snapshot registry, experiment records
  ├─ Python worker: extraction/chunking → embeddings → snapshot preparation
  ├─ Python search: snapshot pin → dense search + Go sparse RPC → RRF
  └─ Go node: validated immutable segments and snapshot-scoped search

Artifact store: source files / corpus snapshots / segment files / embeddings
```

Use PostgreSQL for metadata and a leased job table; do not add a second broker in this milestone. Scope is a configured local principal, not production end-user authentication. Bind development endpoints locally. Preserve a clear authorization seam for weeks 5–6 and require authenticated service calls at the RPC boundary.

## 1. Segment format and reader/writer

Promote the exact format in the earlier plan to `docs/contracts/segment-format-v1.md`; that layout is authoritative:

```text
[96-byte Header | Chunk Table | Term Dictionary | Delta-Encoded Postings | 32-byte SHA-256 Footer]
```

- Unsigned little-endian fixed integers; canonical ULEB128 bounded to 64 bits.
- Header offsets: magic 0, version 8, flags 10, header size 12, file size 16, chunk count 24, term count 32, chunk-table offset 40, dictionary offset 48, postings offset 56, footer offset 64, total tokens 72, zero-reserved bytes 80–95.
- Magic `RLSEG001`, version 1, flags 0, header size/chunk-table offset 96.
- Chunk records: `[ID length varint | UTF-8 external ID | token length varint]`, sorted by ID bytes.
- Dictionary: `[term length varint | UTF-8 term | df varint | postings offset u64 | postings length u64]`, sorted by term bytes.
- Postings: `[chunk gap | tf | tf position gaps]`, all varints. First chunk ID/position is absolute zero-based; subsequent gaps strictly positive. Restart positions per chunk.
- Footer hashes all preceding bytes; manifest hashes the entire file. No padding or trailing data.

Reject malformed UTF-8, overlong/overflow varints, unknown versions/flags, reserved nonzero bytes, invalid bounds/counts/order/positions, inconsistent token totals, duplicate IDs, truncation, and checksum mismatch. Bound allocations before reading attacker-controlled lengths. Do not emit empty segments; support empty collections through zero-segment snapshots and empty search results.

Writer: deterministic bytes, temporary output, flush/close, validate with reader, then immutable publication. Reader: validate once before admission; load dictionary/chunk metadata and decode requested postings through an abstraction. Do not eagerly rebuild the entire in-memory index and call that lazy disk retrieval. Start with bounded random-access reads; memory mapping and skip blocks are later optimizations.

Tests: hand-authored golden bytes, writer/reader round trips, malformed-file fuzzing, and rank/phrase parity against the weeks 1–2 in-memory reference.

## 2. Snapshot identity and consistency

Keep three identities distinct:

| Identity | Meaning |
|---|---|
| Corpus snapshot | Exact normalized papers/chunks |
| Retrieval snapshot | Corpus + segments + analyzer/statistics + embedding artifacts/configuration |
| Run | Query/configuration against one retrieval snapshot |

Retrieval manifest records collection ID, corpus hash, ordered segment hashes, aggregate statistics hash, embedding manifest hash or explicit absence, analyzer version, schema version, and capability set. Its content hash excludes timestamps. Scope/ownership belongs to registry metadata and must also be verified, not inferred from a hash.

Segments have disjoint external chunk IDs. Compute `N`, total token count, average length, and per-term df across the complete snapshot; never merge rankings scored with unrelated segment-local statistics. Score candidates consistently and apply deterministic external-ID tie-breaking globally.

### Activation protocol

1. Write all source/corpus/segment/vector artifacts to staging, then publish verified immutable files.
2. Register a `prepared` snapshot and its complete manifest in PostgreSQL.
3. Ask the Go node to load/validate that explicit snapshot; validate dense artifacts in Python.
4. Mark the snapshot `ready` only when all declared capabilities are usable.
5. Compare-and-swap the collection's active snapshot against the job's expected parent in one database transaction.
6. Queries resolve the active ID once, pin it for all retrieval and passage reads, and return it in results.

The registry is the active-pointer authority; avoid independent filesystem and database “current” pointers. Artifact writes and DB transactions are not one atomic transaction: handle the intermediate states explicitly. A stale writer must not overwrite a newer active snapshot. A lost activation response is reconciled by inspecting registry state before retrying.

If a required node is unavailable, return an explicit error; never silently query an older/latest alternative. On restart, load the registered snapshot before readiness. A missing/corrupt active artifact fails closed and requires explicit recovery to a retained valid snapshot.

Keep old snapshots for pinned requests and saved runs. No automatic artifact garbage collection in this milestone. Document supported OS/filesystem flush behavior; process-crash tests do not prove power-loss durability.

## 3. Metadata and durable ingestion

Use migrations and database constraints. Proposed tables:

| Table | Key data |
|---|---|
| `principals` | Stable local principal; later external identity mapping |
| `collections` | Owner principal, visibility, active retrieval snapshot |
| `paper_versions` | Logical paper/version IDs, source hash and provenance |
| `collection_papers` | Collection membership and selected paper version |
| `ingestion_jobs` | Scope, idempotency key, input/config hashes, state, lease, attempts, expected parent, output snapshot |
| `retrieval_snapshots` | Collection, corpus/manifest hashes, state, capabilities |
| `experiment_runs` | Scope, snapshot, query/config/dataset hashes, status, artifact reference |

Keep immutable chunk content in corpus artifacts initially; do not duplicate all text into PostgreSQL without a demonstrated need.

Job states: `queued → running → succeeded`, with `retry_wait`, `failed`, and `cancelled`. Persist stage/progress independently: extract, chunk, sparse build, embed, validate, activate. A job succeeds only after activation is reconciled.

- Claim jobs transactionally using row locks with skip-locked semantics; pin exact SQL behavior to the selected PostgreSQL version.
- Use database time for lease expiry. Each claim increments a fencing token; heartbeats, checkpoints, and finalization require the current token.
- At-least-once processing with idempotent outputs, not an exactly-once claim.
- Uniqueness on collection plus idempotency key; a repeated key with different input/configuration is a conflict.
- Bound attempts; use backoff for transient failures and explicit terminal errors for corrupt inputs.
- Reclaim expired leases. A stale worker cannot activate or overwrite current progress.
- Serialize collection builds or reject stale-parent activation and rebuild against the latest collection membership.
- Store safe failure summaries; source text and credentials do not belong in logs.

Start with text-PDF ingestion. OCR-required or extraction-failed papers receive explicit status; never index fabricated or empty content as successful.

## 4. Go–Python gRPC contract

Implement the gRPC/Protobuf decision from weeks 1–2. Pin code-generation tools and keep generated bindings consistent. Existing HTTP and gRPC adapters call the same Go search functions until parity is established.

| RPC | Contract |
|---|---|
| `Search` | Service identity, authorized collection/scope, explicit retrieval snapshot, query/mode, candidate limit, explanation flag → ranked chunk IDs, scores, snapshot/config IDs, timings |
| `GetSnapshotInfo` | Explicit scope/snapshot → readiness, versions, counts |
| `PrepareSnapshot` | Worker-only control operation referencing a registered immutable manifest → idempotent load/validation status |

`PrepareSnapshot` is a justified extension of the earlier contract. Go resolves manifests through configured storage; never accept arbitrary filesystem paths from callers. It prepares an ID but does not change the database active pointer. Restrict control calls separately from read calls.

Use unary bounded messages initially: up to 1,000 candidates, 4,096 query characters, and 4 MiB messages. Return IDs and bounded explanations; Python reads passage text from the pinned corpus. Reuse channels, set deadlines, propagate cancellation, bound concurrency, and map failures to defined gRPC statuses. Retry only transient read/prepare failures within the original deadline against the same ID.

Local service credentials stay outside Git; cross-host transport must authenticate and encrypt. A scope string alone grants no access. Reserve deleted Protobuf field numbers/names and validate unspecified enum values. Test Python-generated clients against the live Go server.

## 5. Exact dense retrieval

Select one modest CPU-capable embedding model after inspecting current official model documentation, license, revision availability, query/document formatting, dimensions, context limit, and resource use. Record the choice in an ADR; cloud inference is optional, not a baseline dependency.

Embedding manifest records model/revision, tokenizer/pooling configuration, query/document prefixes, dimension, dtype, normalization, source chunk hashes/order, and software versions. Cache by content plus complete model/configuration identity; no reuse across incompatible settings.

Use finite float32 vectors and normalized dot products for cosine similarity. Reject invalid dimensions, NaNs, infinities, and zero-norm vectors. Preserve the exact ordered chunk-ID mapping. Compute exhaustive search in bounded blocks; deterministic external-ID tie-breaking. Validate against a small independently computed cosine fixture. Record tolerance and hardware-related numerical variation.

Analyzer tokens and model tokens differ. Check model input lengths independently. Do not silently truncate: record a versioned truncation policy/count or reject and rebuild chunks under an explicit new configuration.

CI uses deterministic test embeddings for plumbing; those are not quality evidence. Actual dense-quality reports must use the recorded real model. Run model-download smoke checks separately from ordinary offline CI.

## 6. Hybrid search and failure semantics

For ranked list `L`, one-based rank `r`, and initial `k=60`:

```text
RRF(chunk) = sum(1 / (k + rank_L(chunk)))
```

Missing list membership contributes zero. Deduplicate each input by chunk ID, accumulate across lists, then rank globally. Keep BM25, cosine, and RRF values separate. Start with 100 candidates from each retriever and 10 final hits; expose limits/configuration for experiments. Tie-break by external chunk ID. Test overlap, disjoint/empty lists, duplicate IDs, and equal totals.

Support free-text sparse, dense, and hybrid modes. Structured Boolean/phrase queries remain sparse-only in this milestone; explicitly reject dense/hybrid structured requests. Silently treating a Boolean expression as semantic text or filtering only a truncated dense top-k would violate the earlier grammar. A future complete eligible-ID filter can extend this contract.

Both branches and passage lookup must use the same retrieval snapshot. Do not fuse different corpora or model versions. Default hybrid failure is explicit; any optional degraded sparse-only response must identify the missing branch and must not be reported as hybrid evaluation.

## 7. Evaluation and operational evidence

Preserve the earlier dataset/version history. Pool new dense/hybrid candidates for owner review; do not assume unjudged results are irrelevant. Freeze development configuration before evaluating held-out queries. If the old held-out set was repeatedly inspected, label it development and create fresh held-out questions.

Compare sparse, exact dense, and hybrid on the same snapshot/query set using nDCG@10, MRR@10, known-positive recall, judgment coverage, and query failures. Report per-query changes and paired aggregates; a small reviewed dataset supports exploratory findings, not sweeping superiority claims.

Measure segment size/compression, build/load time, peak memory where available, query p50/p95, embedding time, and hybrid stage timing. Compare disk and in-memory ranking parity, plus HTTP/gRPC equivalent workloads. Record cold/warm conditions, counts, hardware, versions, and all exclusions.

Required failure experiments:

| Injection | Expected result |
|---|---|
| Truncate/corrupt a segment | Validation rejects it before activation |
| Kill worker before/after artifact publication | Retry reuses verified outputs or rebuilds; active snapshot unchanged |
| Lease expires while old worker returns | Fencing blocks stale completion |
| Two builds share the same parent | One activation wins; stale build cannot overwrite it |
| Activate while a query runs | Query uses one old or new complete snapshot throughout |
| Restart Go after activation | Explicit snapshot is reloaded before serving |
| Embedding failure or incompatible vector manifest | No ready hybrid snapshot published |

## 8. Fourteen commit-sized steps

Each step includes implementation, focused tests, documentation, and a separate commit. Preserve logical commits through PR merges; extra fixes are allowed. Update implementation status with commit IDs and actual evidence.

| Step | Commit message | Deliverable and gate |
|---|---|---|
| 1 | `docs: define persistence snapshot and RPC contracts` | Audit prerequisites; canonical format, lifecycle, schema and naming ADRs |
| 2 | `feat: write deterministic compressed segment files` | Writer and golden-byte/checksum fixtures |
| 3 | `feat: read validated disk-backed postings` | Bounded decoder, corruption tests, in-memory ranking parity |
| 4 | `feat: search immutable multi-segment snapshots` | Aggregate statistics, global ranking, pinned reader lifecycle |
| 5 | `feat: add PostgreSQL collection and snapshot registry` | Migrations, constraints, active-pointer CAS tests |
| 6 | `feat: publish and recover prepared snapshots` | Stage/prepare/activate lifecycle; interrupted publication tests |
| 7 | `feat: serve retrieval through generated gRPC contracts` | Search/info/prepare RPCs, service identity, HTTP parity |
| 8 | `feat: add leased idempotent ingestion jobs` | Claims, fencing, checkpoints, retries, stale-worker tests |
| 9 | `feat: orchestrate recoverable collection ingestion` | Text import through activated sparse snapshot; restart demo |
| 10 | `feat: build versioned embedding artifacts` | Real-model adapter, cache identity, bounded batches, fixture adapter |
| 11 | `feat: implement exact dense candidate retrieval` | Cosine reference parity, stable IDs, invalid-vector tests |
| 12 | `feat: fuse snapshot-pinned sparse and dense search` | RRF, explicit mode/failure rules, consistent hybrid activation |
| 13 | `test: evaluate hybrid retrieval and recovery behavior` | Reviewed pool expansion, three-mode report, required failure cases |
| 14 | `docs: package reproducible hybrid milestone demo` | Local Compose/setup, pinned dependencies, clean-start rehearsal and next backlog |

Steps 10–12 extend sparse snapshots with new immutable hybrid snapshots; never mutate an existing snapshot to add embeddings. Prepare review batches early while independent work proceeds.

## Acceptance and handoff

- Segment bytes and ranking match the specified format/reference; invalid files fail safely.
- Restart loads indexes without rebuilding from paper text.
- Search pins one snapshot across Go, vectors, and evidence reads.
- Job retries and competing writers do not duplicate activation or overwrite newer state.
- Generated Python gRPC clients pass integration, scope, timeout, and cancellation tests.
- Sparse/dense/hybrid runs are replayable with real-model identity and reviewed-label coverage.
- Offline CI runs with PostgreSQL and deterministic fixtures; real-model evidence is reported separately.
- Update `docs/reports/week-04-baseline.md`, architecture/contracts, and implementation status. Link measured artifacts; list unfinished gates explicitly.

Demo: ingest → search three modes → restart Go → repeat ranks → interrupt/recover ingestion → inspect pinned snapshot IDs → show benchmark and one failure case.

## Implementation task prompt

> Read this handoff completely, then read Plans/ENGINEERING_WORKFLOW.md, prerequisite plans, repository instructions, and implementation status. Follow every approval boundary. Work only on the first incomplete commit-sized step: propose its branch, scope, checks, and commit message, then wait for branch approval before changing code. After approval, implement and validate only that step, present the complete diff and results, and wait for commit approval. Do not work directly on main, push, open or merge a pull request, or begin another step without the required authorization. Keep repository language natural and project-focused, preserve unrelated work, and report actual evidence and incomplete gates.
