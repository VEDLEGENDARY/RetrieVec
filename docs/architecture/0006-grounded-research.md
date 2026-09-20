# ADR 0006: pinned research runs and tool-free generation

Status: implemented; model quality acceptance remains pending human review.

Store each request, effective query, snapshot identity, model/configuration hash,
result and selected evidence in PostgreSQL. A replay explicitly chooses the
historical or current snapshot and creates a new run with parent lineage. An
idempotency key is scoped to owner/conversation and rejects changed payloads.
Follow-ups use a user-visible standalone query; no hidden model rewrite or
implicit transmission of the entire conversation occurs.

Use llama.cpp's native tokenize/completion API with a pinned ChatML model.
Tokenize the complete prompt, reserve output capacity, and exclude whole
passages that do not fit. Document control markers are JSON-escaped; generation
receives no tools. Provider-constrained citation IDs and whole-passage quotes
reduce avoidable invalid outputs, but strict post-generation checks remain
mandatory. A validation failure is an explicit failed run, with no automatic
extra inference call. Numerical literal membership is only a structural check.

A separate single-consumer worker holds an advisory lock. Each attempt has a
30-second lease, two-second heartbeat and fencing token. Stages/results/events
are transactional. Expired attempts become failed, never automatically retried,
because a cloud timeout can leave billing uncertain. The operator starts only
one generation consumer; each user may queue at most three active runs.
Retrieval uses its existing bounded RPC deadline; combined tokenization and
generation have a 240-second outer deadline. HTTP cancellation closes the
connection, but cannot guarantee the remote provider stops billing.

Progress uses finite SSE batches with monotonic IDs and cursor/header resumption.
Each request rechecks the session and resource. The UI polls the persisted run
snapshot, including completed results, rather than showing unvalidated tokens.
Cloud consent is off by default and tied to the entire provider configuration.
Archive revokes resource reads and fences active work. Consent revocation stops
active requests for that provider; it does not physically erase retained results.

Exports materialize stored results into private, twenty-minute database records.
No filesystem download paths or bearer links are exposed. Original source reads
remain independently authenticated and snapshot/hash checked. Missing originals
are explicit; retained curated passages can exist without uploaded originals.
