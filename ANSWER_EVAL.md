# Answer quality evaluation

The phase 4 harness evaluates the authenticated application research API, including
snapshot-pinned retrieval, evidence packing, generation, structural validation,
live source checks, and saved-run publication. It does not supply oracle passages.

## Dataset and provenance

`datasets/answer_quality/questions-v1.json` contains 72 **synthetic questions** over
24 retained SciFact title/abstract records. Development and validation each have
six questions; the test split has 60. Each split has disjoint paper IDs and
question texts. Every paper contributes an answerable, partially answerable, and
unanswerable template. These expectations are drafts, not human judgments.

The corpus manifest binds exact source bytes with SHA-256. The harness requires
the selected authorized active snapshot to match a local immutable retrieval
manifest whose corpus contains exactly those sources. Foreign evidence or a
changed provider identity fails the case. No default retrieval setting changes.

## Run and review

Use an existing signed-in evaluation session. A private session JSON contains
`session_cookie` and `csrf_token`; keep it outside tracked files. The following
command creates saved conversations and runs in the selected collection:

```sh
python scripts/evaluate_answers.py run --origin http://127.0.0.1:8000 \
  --session artifacts/private-session.json --collection COLLECTION \
  --snapshot RETRIEVAL_SNAPSHOT_ID --store artifacts/store \
  --providers local-qwen-1-5b --output docs/results/answers-2026-10-05.json
```

One provider is supported for the user's requested Qwen2.5 1.5B run. Supply a
second configured provider to compare both against the same isolated test split.
Cloud providers must already have explicit collection consent; the harness never
grants it. The stronger-provider comparison is deferred at the user's request.

```sh
python scripts/evaluate_answers.py export-review REPORT.json artifacts/review.json
python scripts/evaluate_answers.py import-review REPORT.json artifacts/review.json REVIEWED.json
python scripts/evaluate_answers.py judge REPORT.json --config configs/providers.json \
  --provider JUDGE --origin http://127.0.0.1:8000 \
  --session artifacts/private-session.json --output JUDGED.json
```

Human export fields start blank. Import requires reviewer identity, a dated review,
an assessment of every claim/passage and comparison/passage pair, faithfulness,
and abstention correctness. Hash bindings reject a review of changed evidence.
The optional LLM judge is labeled automatic and does not populate human review.
Judge-vs-human agreement is null unless a reviewed overlapping subset exists.

## What the metrics establish

Citation precision asks whether the cited passage supports its specific claim.
An exact quote or valid citation ID alone does not establish that. Faithfulness
and semantic citation precision remain null without a human review or labeled
judge assessment. Automatic abstention correctness compares the answer/abstain
decision with the synthetic template expectation; it is not semantic accuracy
and does not grade the completeness of partially answerable responses.

End-to-end latency includes API submission, queueing, generation, and polling.
TTFT is measured from worker start to the first nonempty model content token,
excluding queue time. Nonstreaming, no-evidence, and failed runs may have no TTFT.
Failures are retained and excluded from successful-answer metric denominators.

## Recorded Qwen2.5 1.5B results

[Measured report](docs/results/answers-2026-10-05.json): all 60 test cases have
recorded outcomes; only 11 completed the pipeline. The local Q4_K_M model used
4,096 context tokens, 1,024 output tokens, temperature 0 and seed 42. Its exact
weights hash and provider identity are retained in the report.

| Synthetic question kind | Completed | Failed | Published answer status |
|---|---:|---:|---|
| Answerable | 4 / 20 | 16 / 20 | 1 answered, 3 partial |
| Partially answerable | 7 / 20 | 13 / 20 | 7 partial |
| Unanswerable | 0 / 20 | 20 / 20 | None |

There were 48 `invalid_answer` failures and one `provider_failed` failure. The
automatic binary abstention score is 11/11 among completed cases only: all those
templates expected a non-abstaining response. It says nothing about the failed
unanswerable cases, completeness, or semantic accuracy. Human and LLM-judge
citation precision, faithfulness and abstention scores are all **null**.

Successful-case end-to-end p50/p95 were 64,158 / 90,332 ms; worker TTFT p50/p95
were 37,524 / 43,915 ms (11 samples). The run resumed after a host pause and
database timeout, retaining original failures. These timings describe this CPU
run across sessions, not a controlled production performance comparison.
The real API, PostgreSQL, Go retrieval and llama server were used through ASGI;
an explicit isolated local evaluation session bypassed OIDC login. Application
source was frozen at `2b78b88` throughout the run.

**NLI check: NOT run. Human review: not performed.** Every human-review field
remains blank. The stronger-provider comparison remains deferred at the user's
request. These are **synthetic-question, automatic-only** results.
No model weights, original paper PDFs, sessions, or credentials belong in the
evaluation commit. Abstract-only synthetic results do not establish full-paper
answer quality, production readiness, or superiority to another model.
