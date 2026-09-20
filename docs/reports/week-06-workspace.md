# Week 6 research workspace handoff

This handoff covers Weeks 5–6 steps 8–14. The workspace now persists owned
conversations and snapshot-pinned runs, supports local and explicitly consented
cloud generation, validates cited answers, streams resumable progress, exports
stored results, and exercises isolation through the real Python/Go/PostgreSQL
browser flow.

## Reproduction

Run the commands in [workspace setup](../workspace-setup.md). The required local
checks are:

```text
python scripts/check.py
python scripts/check.py --race       # Linux with a C compiler
cd web
npm ci
npm run build
npx prettier --check src tests playwright.config.ts vite.config.ts
npm test
```

The hosted integration job uses PostgreSQL 18.3, runs the generated-RPC check,
Go tests/fuzz smoke, the Python suite, the production frontend build, and the
real browser flow. The browser flow starts a signed test OIDC issuer, real
FastAPI and Go services, an isolated PostgreSQL schema, and deterministic
embeddings/generation. These fixtures are for repeatable CI plumbing and are
not a model-quality claim.

## Provider and hardware record

The real local smoke used llama.cpp b11064 on an Intel Core Ultra 7 155H with
16,597,598,208 bytes of RAM, four CPU threads, no GPU layers, one slot, and a
4096-token context. The model was Qwen2.5-1.5B-Instruct-GGUF Q4_K_M, revision
`91cad51170dc346986eccefdc2dd33a9da36ead9`, Apache-2.0. The runtime and model
hashes are recorded in [workspace setup](../workspace-setup.md).

The twelve-case synthetic smoke set took 9,848–22,986 ms per non-empty request
(median 19,941 ms; mean 18,391 ms). Eleven cases had evidence and one was an
empty-evidence abstention. The final structural recheck is saved as
`week-06-validation-recheck.json`; it made no provider calls. The smaller
0.5B baseline rejected all eleven evidence cases because its output did not
meet the answer contract, while its empty-evidence path abstained correctly.
The 1.5B run produced structurally valid output for most cases, but the packet
shows relevance and attribution weaknesses that still require human review.

## Review status and limits

The owner chose to leave human review pending. There are zero completed human
reviews. [The review packet](week-06-answer-review.md) contains all twelve
questions, expected behavior, model output or rejection, and blank review fields.
Do not treat structural citation validity, exact quote membership, or generated
self-assessment as semantic support. Do not use this synthetic set as a held-out
scientific benchmark; the set was reused after the provider/prompt change.

Open acceptance gates are human claim support, citation completeness,
unsupported-number review, abstention appropriateness, task completion, broader
real-corpus retrieval evidence, and a local Keycloak end-to-end smoke. Docker and
Keycloak were unavailable in the local environment; hosted CI covered the
signed-issuer protocol flow and database/browser integration.

## Commits and PRs

Steps 8–13 are preserved as separate commits on feature branches and are grouped
into regular (non-squash) pull requests. Step 14 is this handoff commit on
`docs/research-workspace-handoff`. The merge plan is PR 20 (step 8), PR 21
(steps 9–11), PR 22 (steps 12–13), then the handoff PR. Direct pushes to `main`
are not used.

## Weeks 7–8 backlog

Complete the owner-reviewed answer set and held-out real-corpus evaluation;
profile provider/retrieval latency and load; add retention and disaster-recovery
drills; exercise local Keycloak; expand hostile-file and cancellation/load tests;
improve model prompting or choose a better licensed local model based on review;
and prepare a reproducible portfolio demonstration. OCR, advanced extraction,
public deployment, and physical purge remain separate decisions.
