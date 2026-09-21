# Reproducing workspace measurements

No Weeks 7–8 measurements were executed in this implementation batch. Existing
[week-04 measurements](reports/week-04-baseline.md) are historical component evidence,
not a current end-to-end baseline. No retrieval optimization is justified yet.

Use an isolated synthetic collection and an authenticated local workspace. Save a
short-lived session privately as JSON with `session_cookie` and `csrf_token` keys
under ignored `private/`. Never commit it. Save questions as a JSON array of strings;
the load record retains question hashes, not question text or answer payloads.

```powershell
python scripts/load_workspace.py --profile concurrent-search --session private/session.json --collection COLLECTION_ID --queries private/questions.json --output artifacts/load/search-01 --corpus-size 100 --server-pid 1234 --server-pid 5678
```

Replace the example count and PIDs with actual corpus size and server processes.
Identify API, Go, ingestion, research and model-server PIDs individually; child
processes are not included automatically. CPU/RSS sampling supports Windows and
Linux, includes warmup, counts errors and detects PID reuse. CPU percentage is in
units of one logical core. Sampled peak RSS can miss sub-second peaks. Without PIDs,
CPU/RAM is explicitly unavailable. Do not compare process memory figures as if they
were whole-machine memory. Record model revision, threads, corpus/chunk count,
resident services, OS, CPU/RAM and background load in the accompanying report.

| Profile | Default concurrency / measured count | Behavior |
|---|---|---|
| single-researcher | 1 / 10 | Search, saved answer, export |
| concurrent-search | 4 / 40 | Three-mode search with overloads counted |
| mixed-ingestion-search | 2 / 12 | Alternate synthetic uploads with search/answers |
| slow-provider | 2 / 8 | Research against an explicitly configured slow provider |

Mutating profiles require `--allow-mutations`. Slow-provider additionally requires
`--slow-provider-confirmed`; the tool does not substitute a fake provider or claim
its output is model evidence. Retained run/job/collection IDs are in both warmup
and measured JSONL files. The runner creates synthetic collections for mixed uploads;
archive those through the workspace after inspection. It never deletes source data.

Limits: at most eight clients, 500 measured requests, 20 warmups, 360 seconds per
workflow and 3600 seconds total scheduling budget. Timed-out runs receive a best-effort
cancellation request. Cleanup may extend the wall budget by up to five seconds per
active failed run. Every scheduled measured request contributes an outcome, including
timeouts and exhausted wall budget. Reports include all-outcome and success-only
p50/p95 separately. Failed warmups are retained separately. HTTP wall time includes
queueing/network/model overhead; server retrieval and research timings are separate
fields and must not be added to wall time. Keep `requests.jsonl`, `warmup.jsonl`,
`report.json` and private-safe telemetry together under a unique output directory.

Run repeated baselines on the owner's hardware before choosing a budget. Define a
bottleneck and hypothesis, change one variable, demonstrate rank/result parity,
then repeat the same workload/configuration. Record failed runs rather than selecting
only fast runs. No universal latency target or speedup is claimed by this milestone.

## Reviewed quality and paired uncertainty

Use [labeling instructions](../datasets/evaluation/LABELING.md) to expand toward
40–60 genuinely reviewed retrieval questions and a smaller answer set. Preserve
reviewer/rationale provenance. Keep answer support, citation completeness, abstention
and structural failures separate. The existing twelve-answer packet remains pending.
Previously inspected questions cannot establish a fresh held-out result.

After actual review, freeze the dataset against **all** previously exposed datasets:

```powershell
python scripts/freeze_evaluation.py private/reviewed.json --corpus artifacts/CORPUS --prior-dataset datasets/evaluation/synthetic-draft-v1.json --output artifacts/evaluation/frozen-01
python scripts/compare_evaluations.py artifacts/left/metrics.json artifacts/right/metrics.json --output artifacts/paired-01.json
```

The freeze rejects incomplete review, exact normalized held-out overlap and duplicate
questions. It cannot recognize paraphrases or verify a person's asserted review.
Pair comparisons require the same dataset, split, cutoff, draft policy and query
universe. They report right-minus-left query-paired bootstrap intervals, sample
counts, excluded undefined pairs, missing queries and failures. Small samples and
success-conditioned comparisons do not establish broad superiority. Evaluate the
exact demo configuration; do not tune repeatedly on the held-out set.
