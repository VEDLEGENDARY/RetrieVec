# Stage 2.3 reranker and answer-quality study

The cross-encoder is an opt-in experiment. The default hybrid ranking remains unchanged.
The measured aggregates and artifact identities are saved in
[`answer-quality-stage-2.3.json`](answer-quality-stage-2.3.json).

The pretrained baseline is `cross-encoder/ms-marco-MiniLM-L6-v2` at commit
`9cc09816f0a7a8aaceefa40a3cfbb843c1bfa579` (Apache-2.0). The local
`onnx/model.onnx` SHA-256 was
`5d3e70fd0c9ff14b9b5169a51e957b7a9c74897afd0a35ce4bd318150c1d4d4a`.
Inference used ONNX Runtime 1.30.0 on CPU, batch size 8, up to 512 pair tokens,
and rejected oversize pairs rather than silently truncating. The
[model card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) describes
the model as trained for MS MARCO passage ranking; transfer to scientific papers
must be measured rather than assumed.

The full sweep used all 300 held-out SciFact queries in the frozen benchmark
order, with the tuned hybrid configuration and pinned retrieval snapshot
`rs_04aeda526518bfae58388140b4d24d77fa03a259424f6983e1797db754aca752`.
The exported candidate-pool SHA-256 was
`19ae3c13624adf9ec8e78891f7733f421c4faddedb403318d3b55f693b65f3c3`.
Judgments are BEIR paper-level qrels, not human-reviewed PDF questions. Timings
measure reranking only, after model load and candidate retrieval. The test qrels
SHA-256 was `0864bb985e0ca2367ba217977e72004d549054b2b06666ed9d4825ac7c21284c`.
All 300 query pools were unique and all three runs had zero query failures.

| Hybrid candidate limit | Baseline nDCG@10 | Reranked nDCG@10 | Candidate recall | Rerank p50 / p95 |
| ---: | ---: | ---: | ---: | ---: |
| 20 | 0.6836 | 0.6710 | 0.8472 | 551 / 742 ms |
| 50 | 0.6847 | 0.6694 | 0.9213 | 1583 / 2182 ms |
| 100 | 0.6847 | 0.6657 | 0.9487 | 2100 / 3448 ms |

The reranker-minus-plain-hybrid nDCG@10 differences have query-paired 95%
percentile bootstrap confidence intervals (5,000 resamples; seed 1729;
300 paired queries and zero exclusions at each candidate limit):

| Candidate limit | Paired nDCG@10 delta | 95% confidence interval |
| ---: | ---: | ---: |
| 20 | -0.0126 | [-0.0363, +0.0121] |
| 50 | -0.0153 | [-0.0417, +0.0124] |
| 100 | -0.0190 | [-0.0460, +0.0096] |

These descriptive intervals include zero; the observed losses do not establish
a statistically clear degradation. The added latency and lack of demonstrated
quality gain still support retaining the default. Per-query scores were recovered
by replaying the pinned model against the same hashed pools; every aggregate
matched the original sweep. Latencies above remain from the original uncached run.

**Decision: reject this pretrained reranker as a default.** At 50 candidates it
lost 0.0153 nDCG@10 while adding 1583 ms p50; the observed quality-per-
millisecond is negative. Preserve the unchanged hybrid reference and the opt-in
adapter for further study. This decision covers SciFact paper ranking, not answer
faithfulness or the pending reviewed PDF question set.

### Reranker diagnosis and opt-in blend

The tested model was `cross-encoder/ms-marco-MiniLM-L6-v2` at the pinned revision
above. Its maximum sequence length was 512 tokens, including query, passage and
special tokens. Across all 30,000 candidate occurrences, the longest pair had
206 tokens: **no candidate text was truncated**. The adapter passed `(query,
chunk.text)`; it did **not** concatenate the paper title with every chunk. A full
title happened to occur in 3,496 chunk texts (11.65%), so title coverage was
inconsistent. Missing title context is a possible explanation, not a tested cause.

One fixed blend was evaluated on the same 300 queries and top-50 candidate pools:
`0.5 * minmax(hybrid_rrf_score) + 0.5 * minmax(reranker_logit)`, normalizing each
score vector within its query pool (constant vectors map to zero). Ties use
ascending chunk ID; paper IDs are then deduplicated and the query paper excluded.
Actual hybrid scores were recovered by replaying the pinned retrieval pipeline;
all 300 candidate orders matched the saved pools exactly. No blend-weight search
was performed.

| Top-50 ranking | nDCG@10 | MRR@10 |
| --- | ---: | ---: |
| Plain hybrid | 0.6847 | 0.6456 |
| Reranker replaces hybrid order | 0.6694 | 0.6300 |
| Equal-weight score blend | 0.7016 | 0.6639 |

The blend improved nDCG@10 by **+0.01694 versus plain hybrid**, with a paired 95%
bootstrap interval **[+0.00004, +0.03474]**, and by +0.03219 versus replacement
([+0.01270, +0.05243]); 5,000 resamples, seed 1729, 300 pairs, zero exclusions.
This is recorded as the new **opt-in experimental variant
`hybrid-minilm-minmax-blend-50`**. This is a post-hoc result on an already-inspected
test set, with a lower interval endpoint very close to zero; fresh held-out
validation is needed. It still requires cross-encoder inference; blend latency
was not independently measured. This report records an offline variant, not a
new runtime switch. **No default or runtime ranking behavior changed.**

Reproduce with an already prepared `artifacts/beir` benchmark and the pinned
model files cached locally:

```powershell
.venv\Scripts\python.exe scripts/export_reranker_pools.py --dataset scifact --output artifacts/beir/scifact/reranker-pools-full.json
.venv\Scripts\python.exe scripts/eval_reranker.py --input artifacts/beir/scifact/reranker-pools-full.json --output artifacts/beir/scifact/reranker-sweep-full.json
```

Answer-level signals are automatic diagnostics only. Structural validity,
exact-quote coverage and numeric-literal checks are generated from the existing
answer validator; lexical overlap is explicitly **not NLI**. A true NLI proxy
requires separately pinned ONNX artifacts and label order. Human support,
citation, abstention and task-completion fields remain blank until reviewed.
**The NLI check was NOT run.** The saved run has no NLI configuration; its
lexical-overlap diagnostic is not an entailment or faithfulness judgment.

Two pinned local Qwen2.5 GGUF models were also run on the **same 12 synthetic
questions and the same current prompt**. These are **synthetic-question,
automatic-only results**. The 0.5B model passed structural
validation on 12/12 outputs (median 19.0 s); the 1.5B model passed on 9/12
(median 17.6 s). The 1.5B failures were two `partial` objects without claims
and one unsupported project measurement. These are protocol and latency
diagnostics, not a semantic-quality ranking: the 0.5B model's 12 structurally
valid answers may still be factually wrong. The models were served locally from
GGUF files verified against the SHA-256 revisions in
`configs/generation.evaluation.example.json`. The 24 exported human-review rows
all remain blank. The synthetic set is not the requested 50–100 passage-linked,
human-reviewed PDF question set.

```powershell
.venv\Scripts\python.exe scripts/eval_answers.py --dataset datasets/evaluation/answers-v1.json --providers configs/generation.evaluation.example.json --model qwen-0.5b --model qwen-1.5b --output artifacts/generation/answer-eval-two-models-v1.json --review-output artifacts/generation/answer-review-two-models-v1.json
```
