# Workspace and evaluation maintenance pass

This pass covers answer evaluation, shared client behavior, application structure,
and the research UI. It preserves the existing retrieval defaults, pinned models,
authorization boundaries, and stage 2.3 measurements.

## Correctness and reliability

- Hybrid baseline metrics are collected independently of reranker success.
  Paired comparisons identify failures on the correct side and calculate gains
  only over matching successful queries. Unjudged runs cannot establish quality.
- Ranking rejects non-finite custom-model scores and empty candidate text.
  Native ONNX loading/inference failures become recoverable runtime errors with
  their original causes preserved, enabling the existing hybrid fallback.
- Answer datasets reject empty sets, malformed questions, duplicate evidence,
  and incorrectly typed flags before provider calls.
- New answer evaluation artifacts include exactly the evidence packed for the
  model, its effective query, and failure information. Review exports retain
  that context and leave all human labels blank. Older artifacts without packed
  evidence export `null`; they are not reconstructed or presented as complete.
- Shared report publication rejects non-finite JSON values, prevents output/input
  path collisions, and atomically replaces each file after flushing it. A failed
  publication preserves the previous file. Two output files are not a single
  filesystem transaction.
- Client network errors and malformed success responses have actionable messages;
  cancellation remains distinct from failure.

## Structure and product experience

The collection sidebar and signed-out welcome screen now have separate components.
The reranker sweep uses shared scoring, summary, and paired-report helpers.
Unused styles for the retired overview dashboard were removed.

The interface uses slate surfaces, teal actions, readable evidence typography,
and a clearer hierarchy between collection navigation, question mode, and the
question composer. Shared tokens carry the update across Ask, Sources, and Saved
research. The welcome screen explains the source-to-evidence workflow. Mobile
navigation, keyboard shortcuts, drafts, and light/dark support remain available.

Under **Evaluate retrieval**, **Experimental reranking** is explicitly opt-in and
available only for natural-language hybrid search. Changing retrieval method or
syntax resets it. Results disclose whether reranking was applied or the request
fell back to hybrid order. This is the existing replacement reranker; the blend
in the stage 2.3 report remains an offline experiment.

## Verification and remaining limits

- `scripts/check.py`: Go vet, tests, build, dependency checks, Python lint/format,
  and 144 Python tests passed (19 database-dependent tests skipped).
- OpenAPI contract and design-token checks passed.
- Frontend production build and 18 browser tests passed, including automated
  accessibility, mobile focus containment, archive undo, drafts, source inspection,
  exports, reranker opt-in/fallback, and network recovery.
- Desktop/mobile screenshots were inspected, including the dark welcome screen.
  Automated accessibility checks do not replace a manual screen-reader review.
- Cached replay of all 300 SciFact queries reproduced every published aggregate
  and paired interval at candidate limits 20, 50, and 100. Replay timing is not a
  new inference benchmark. No historical measurements or human labels were edited.
- Repository review included the request boundaries, snapshot store, authentication
  callback, backup entry point, CI checks, and frontend workflows. This is a scoped
  maintenance audit, not an exhaustive security or load certification.
- Docker's daemon was unavailable locally. PostgreSQL integration, full deployed
  end-to-end tests, container builds, and Go's Linux race check still require CI or
  an appropriate local environment. Existing Lucide bundler warnings remain.
