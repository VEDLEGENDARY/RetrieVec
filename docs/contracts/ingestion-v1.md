# Ingestion v1

Enqueue stages content-hashed local files and a pinned source manifest. Each job
represents the complete desired collection source set, not an incremental append.
Membership changes commit with fenced activation. Concurrent jobs sharing a parent
cannot both replace it; re-enqueue the full desired set against the current parent
after a stale-parent conflict. Idempotency keys cannot change input/configuration.

The worker imports, chunks, optionally embeds, builds sparse segments, registers,
prepares all capabilities and activates. Verified content-addressed artifacts can
be reused after process interruption. Progress is diagnostic; every retry validates
identities again. Registry state is authoritative. Jobs are at-least-once; expired
leases are reclaimable, progress and completion require the latest fencing token.
No automatic artifact deletion occurs. Source text and exception details are not
persisted as error summaries. Cancellation invalidates the lease token.
