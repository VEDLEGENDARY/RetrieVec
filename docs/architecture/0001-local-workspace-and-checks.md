# ADR 0001: Local Go and Python workspace

Status: proposed for owner review with step 1.

## Context

The initial milestone must fit local development on a 16 GB Windows laptop, run
without cloud services, and separate retrieval correctness from experiment tooling.

## Decision

Use one repository with a Go module under `engine/` and an installable Python
package under `python/`. A root Go workspace is unnecessary while there is only
one module. Use `retrievec` for Python imports and `retrievec/engine` for the
local Go module, independent of the Git hosting address.

Begin with standard-library runtime code. Use Python unittest for scaffold tests,
Ruff for lint/format, and setuptools for packaging. Pin development tools and the
build backend. Run the same Python check driver locally and in Windows/Linux CI;
enable Go's race detector on Linux. Pin workflow actions by commit.

Keep generated binaries, data, and local environments ignored. Build corpus and
retrieval functionality in the plan's order, one reviewed commit-sized step at
a time. Add dependencies only when the next capability needs them.

## Consequences

Both languages remain independently buildable. The check driver needs Python
plus Go on PATH, but no Make, Bash, database, downloaded papers, or cloud service.
A single Go module needs no third-party modules or go.sum yet. CI uses synthetic
fixtures as they are added. Tool and action pins require deliberate updates.

HTTP/JSON is the planned initial Python–Go boundary. Persistence and gRPC are
deferred until after the weeks 1–2 milestone.
