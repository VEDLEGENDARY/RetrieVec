# Sparse milestone baseline

Build and validate with `python scripts/check.py`, then run
`python scripts/demo_sparse.py --output artifacts/runs/week-02-demo`.
The demo starts the actual local Go service, captures development queries twice,
verifies ranking equality, replays draft metrics, demonstrates invalid-query
capture, and records warm serial/concurrent latency. Output paths must be new.
Go fuzzing: `go test ./internal/query -fuzz=FuzzParse -fuzztime=5s` from engine.
Go benchmark: `go test ./internal/search -run=^$ -bench=. -benchmem` from engine.

The correctness corpus has 12 synthetic chunks. Twenty draft questions have a
12/8 development/held-out split. All proposed grades remain draft. This report
does not establish real-corpus retrieval quality; actual owner review and corpus
expansion remain open. The previous five-paper extraction audit is documented
in seed-import-v1.md. Measured artifacts and final check outcomes are recorded
in implementation status after the authorized coding batch finishes.

Next dependencies: compressed segments, immutable snapshot manifests, PostgreSQL
registry/leases, generated RPC, real embedding artifacts and snapshot-pinned RRF.
