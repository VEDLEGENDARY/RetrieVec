# Workspace operations and recovery

These commands accompany the uncommitted Weeks 7–8 implementation. They have not
been rehearsed in this batch. Use the existing [setup guide](workspace-setup.md)
for the Python environment, PostgreSQL 18, Go service, OIDC and pinned model setup.
Apply registry migrations before restarting the application and workers; migration
007 adds request IDs and database-time stage timestamps.

## Worker and request behavior

- Ingestion: 60-second leases, 15-second heartbeat, at most three attempts by
  default, bounded exponential retry wait, 120-second extraction subprocess limit.
  A replacement claim receives a new fencing token. Stale workers cannot activate.
- Generation: two-second heartbeat, 240-second generation budget, explicit failure
  after an interrupted attempt. Retry creates a new run; an uncertain cloud request
  may already have incurred a charge. Never reset its state to queued manually.
- Ingestion and generation share one heavy-worker slot. Search is separately
  bounded to two requests per application process. Run one application process
  for the documented local capacity; the search semaphore is not distributed.
- `RETRIEVEC_MAX_PENDING_WORK` defaults to 64 across both workspace queues and may
  be set from 1 through 1024. Queue saturation returns `429 workspace_capacity`.
  Search saturation returns `503 search_busy`. Callers should back off, not spin.
- Cancel through the authenticated UI or `POST /api/v1/runs/<id>/cancel` with the
  session's CSRF token and Origin. Cancellation fences publication. A model server
  may still finish native computation after its HTTP client disconnects.
- Reconnect with `GET /api/v1/runs/<id>/events` and `Last-Event-ID`. Each finite SSE
  batch rechecks session and live collection access; event IDs are persisted.

If PostgreSQL is unavailable, restore connectivity and restart exited workers.
Expired ingestion can reclaim a bounded attempt; expired generation fails on the
next claim. Inspect saved status before retrying. If Go restarts, keep the same
registered snapshots/artifacts and restart the service using the setup guide;
verify a pinned query before resuming a demo. Never replace an active pointer or
delete retained files to make an error disappear. A changed parent requires a new
ingestion request against the current collection.

JSON telemetry on stderr correlates request/job/run/snapshot IDs. `X-Request-ID`
accepts 32 lowercase hexadecimal characters; otherwise the application generates
one. `ingestion.stage`, `stage.finished`, `rpc.finished`, `research.finished`,
`worker.active` and `worker.idle` contain durations and safe state information.
Private prompts, documents, exception strings and credentials are not event fields.

## Offline backup and isolated restore

Stop API and worker writers. Let active work finish or explicitly recover/cancel it
first. Set `RETRIEVEC_DSN` privately in the environment and put PostgreSQL 18 client
tools on PATH. Never paste a credential-bearing DSN into a command or report.
Use protected storage under ignored `private/` or a separate owner-controlled disk.

```powershell
python scripts/workspace_backup.py backup --store artifacts/store --output private/backup-01 --quiesced
python scripts/workspace_backup.py verify private/backup-01
```

`--quiesced` acknowledges that every writer has stopped; it does not stop services.
A failed capture keeps an `INCOMPLETE` marker and must not be restored. The bundle
contains private sources and saved answers; it is not encrypted by this tool.

Separately provision an **empty** PostgreSQL 18 rehearsal database whose name is
`retrievec_restore_` followed by a fresh UUID without hyphens. Set only
`RETRIEVEC_RESTORE_DSN` to that target. Do not point it at the working database.
Then use a fresh artifact destination:

```powershell
python scripts/workspace_backup.py restore private/backup-01 --store private/rehearsal-01/store
```

The tool rejects a working/nonempty target and does not use `--clean`, start
services, overwrite a store or recreate browser sessions. A failed rehearsal is
left for inspection; create another fresh database/directory for the next attempt.
Inspect the returned metadata fingerprints, then use isolated ports and fresh
login sessions to check two-user ownership, historical queries, citations and
exports. Queued jobs remain queued: keep restored workers stopped until deliberately
testing them. Downloaded model weights and identity-provider data outside the store
need their own reproducible configuration or separate backup.

## Deferred acceptance runs

After review, run `python scripts/check.py` with PostgreSQL integration configured,
the frontend build and browser suite from the setup guide, then real provider/load
and isolated restore rehearsals. Include process interruption before and after
publication, exhausted attempts, competing writers, restart, DB outage, cancellation
and revoked-access reconnect. Process-kill tests do not establish power-loss durability.
Record results in [the milestone report](reports/week-08-release.md); this document
does not assert those checks passed.
