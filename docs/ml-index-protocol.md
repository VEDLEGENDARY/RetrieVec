# Model and index experiment protocol

Protocol version: `ml-index-v1`. Status: proposed, no experiment executed.

## Decision boundary

The product retains its existing sparse scorer, exact cosine retrieval and
unchanged model configuration. Experiments are opt-in and cannot change defaults.
The outcome is one of `retain_reference`, `retain_experimental`, or `inconclusive`.
Promotion requires an owner-reviewed decision record; passing infrastructure
checks alone never permits promotion. In this coding-only batch, all execution,
quality review and performance gates remain pending.

Hypotheses:

1. A bounded reranker trained on reviewed training examples improves held-out
   ranking relative to both the unchanged pretrained model and no reranker.
2. An established ANN backend reduces query latency at an acceptable loss of
   exact-neighbor recall without changing scope or snapshot membership.
3. Immutable sparse compaction reduces segment overhead without changing
   external IDs, corpus statistics, structured matches or ranking.
4. One measured sparse optimization improves its observed bottleneck while
   preserving the correct reference implementation.

## Frozen inputs and separation

Create a content-addressed study manifest before mining or training. It records
corpus and retrieval snapshot IDs; query, judgment and split hashes; candidate
pool hashes; code commit and dirty diff hash; dependency lock hash; hardware;
all parameters and random seeds. A changed input creates a new study identity.
Record timestamps as metadata outside deterministic identity inputs.

Assign train, development and held-out membership before producing examples.
Group all paper versions under their logical paper identity. Also group passage
near-duplicates and query paraphrases before splitting. Record the grouping
algorithm/version, normalization, similarity threshold and reviewed exceptions.
Reject cross-split paper, passage-cluster and query-cluster overlap. A missing
cluster assignment or unknown source identity fails the dataset gate.

Training must not read held-out questions, paraphrases, judgments, candidate
passages or paper evidence. Development data supports checkpoint selection only.
Held-out evaluation is opened once after selection is frozen. Later reuse is
recorded and invalidates claims of fresh generalization; prepare a new held-out
set for another tuning cycle.

Each sample records query/chunk/paper/version IDs, split, source text hashes,
judgment ID and grade, reviewer, review state, provenance kind, rationale and
candidate-pool identity. Human-reviewed, synthetic and pseudo-labeled examples
remain distinct. Unjudged passages are not negatives. Ambiguous judgments are
excluded from training until reviewed. Report exclusions and class balance.

The existing draft synthetic question pool does not satisfy this gate. No
reviewed training dataset or frozen study is asserted to exist by this document.

## Reranker procedure

Select a locally supported cross-encoder only after recording its official model
documentation, license, immutable revision and actual hardware smoke result.
Pin tokenizer revision, model file checksums, scoring transformation, pair order,
query/passage prefixes, maximum tokens, batch size and truncation behavior.
Do not choose a moving model revision or load remote model code implicitly.

First capture the unchanged pretrained baseline. Candidate pools are immutable,
snapshot-bound and identical for no-reranker, pretrained and fine-tuned runs.
Record candidate recall separately: reranking cannot recover omitted evidence.
Preserve deterministic external-ID tie breaking. Reject nonfinite scores.

Mine hard negatives from training pools only. Accept reviewed grade-zero
negatives; retain useful/positive judgments separately and exclude unknown or
uncertain candidates. Record miner version, ranks, sampling probabilities, seed,
per-query caps and duplicate exclusions. Never relabel a model score as review.

Training configuration includes loss, optimizer, learning rate, batch and
accumulation sizes, epoch/step limits, sampling, truncation counts, seed,
checkpoint cadence and budget. Save model, optimizer, scheduler, RNG states,
sample order/cursor, progress and complete input/config identities in each
checkpoint. Resume requires matching identities. Publish checkpoints atomically;
an interrupted write cannot replace the last complete checkpoint.

Initial resource ceilings for the 16 GiB laptop: CPU execution, one heavy task,
8 GiB worker memory, 10 GiB output budget, 60-minute run deadline, three epochs
and 1,000 optimizer steps maximum, whichever limit is reached first. These are
safety ceilings, not measured capacity. Fail explicitly on exceeded budgets and
retain the last complete checkpoint. GPU/cloud runs require a separate manifest
and collection-specific processing consent where private data leaves the host.

Select by development nDCG@10, breaking ties by lower measured p95 latency then
checkpoint step. Freeze the selected checkpoint hash and selection report before
opening held-out results. Record failures without silently substituting baseline
scores in a fine-tuned evaluation.

## Approximate retrieval procedure

Use one established cosine-capable ANN backend, selected and version-pinned after
official documentation/license review. No custom ANN algorithm is planned.
Both reference and ANN consume the same validated finite normalized float32
vectors and ordered external IDs from one immutable embedding manifest.

An index belongs to one explicit collection and retrieval snapshot. Authorize
before index resolution; index paths and IDs grant no access. A caller cannot
select a global index and post-filter approximate hits as a substitute for scope
parity. Historical replay resolves its pinned index, never the latest index.

Freeze backend parameters and seed on development queries. Measure exact-neighbor
recall@k separately from relevance nDCG/MRR/known-positive recall and judgment
coverage. Record corpus count/dimension, build seconds, resident/peak memory where
available, serialized bytes, query p50/p95, warmups, samples, failures, distance
counts where supported, and all index/search parameters. Missing counters remain
null with a reason. Toy-dimensional data establishes plumbing only.

## Sparse compaction and optimization

Compaction reads a pinned immutable snapshot with disjoint external IDs and
writes a new segment plus a new manifest. Preserve external IDs, analyzed token
lengths, term frequencies, positions, total token count, document count and
aggregate document frequencies. Duplicate IDs are errors, not last-writer wins.
Preserve embedding and evidence mappings unchanged when corpus content is equal.

Use the existing RLSEG001 format and validated writer. Publish temporary output
only after full validation, then prepare through the existing registry/node
protocol. Activate using the existing expected-parent compare-and-swap. An
activation race loses safely; it cannot replace a newer active snapshot.
Retain every old segment and snapshot while referenced by readers or saved runs;
this study does not enable garbage collection.

Required later execution covers concurrent pinned readers, competing writers,
interruption during output, after immutable publication, during preparation and
after uncertain activation acknowledgement. Compare BM25 scores within the
documented numeric tolerance and exact external-ID order, phrase/Boolean matches,
counts and explanations against the uncompacted reference. Process interruption
does not establish power-loss durability.

Profile before choosing one sparse optimization. Bounded top-k is a candidate,
not an approved conclusion. Preserve the full-sort implementation as reference.
Any disk-layout change requires a new format/version, golden bytes and migration
policy; RLSEG001 bytes must never acquire a new interpretation.

## Decision criteria and reporting

Before measured execution, freeze a decision manifest with numerical latency,
memory, quality and ANN recall budgets chosen from an actual baseline and owner
product requirements. Unset budgets block a retain decision. Do not select budgets
after seeing held-out results. Use paired query-level differences and bootstrap
intervals with seed and sample counts; report no-positive/undefined cases and
judgment coverage rather than silently discarding them.

Retain an experimental reranker only if reviewed quality improves against both
references under the frozen criterion, candidate/support coverage is acceptable,
and failure/resource budgets pass. Retain ANN only if its separate exact-neighbor
recall and judged-quality budgets pass with useful measured resource improvement.
Retain compaction/optimization only after reference equivalence, lifecycle checks
and a measured improvement pass. Insufficient data/resources or inconclusive
intervals retain the reference. A failed experiment is a valid reported result.

Every adapter must later pass private-scope, revoked-access and pinned-snapshot
execution before product enablement. Save config and model/index versions with
every run. Rollback selects the retained reference configuration and its immutable
artifacts without mutating historical runs. No default promotion is implicit.

Artifacts per study: manifest.json, splits.json, pools.jsonl, samples.jsonl,
checkpoints/, results.jsonl, metrics.json, resources.json and decision.json.
Private text, model weights and generated outputs stay in ignored artifact
storage. Commit only approved small manifests and aggregate reports. Publish
actual findings and exact executable reproduction commands in
`docs/reports/ml-index-experiments.md` once the corresponding commands exist.
