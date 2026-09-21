# Workspace hardening and operational evidence

Status: implemented in an uncommitted branch; validation pending.

Use existing PostgreSQL sessions for cross-process worker coordination. Ingestion
and research acquire advisory lock `7823404` before claiming work and keep that
connection outside a transaction during execution. A contending worker returns
without consuming an attempt. Existing leases and fencing still control publication;
an advisory lock is not a replacement for either. A lost database connection can
release the scheduling lock before native computation stops, so this bounds normal
operation rather than guaranteeing zero overlap during a network partition.
Both workers retain their existing single-consumer process guards. Continuous load
may be unfair between worker types; measure starvation before changing scheduling.

Workspace enqueue routes serialize admission with transaction lock `7823405`, then
lock the principal and collection in that order. A configurable combined queue cap
defaults to 64 pending ingestion/research items. Per-user bounds remain in place.
An idempotent research replay of the same request returns its existing run before
checking global capacity. Operator ingestion through the low-level registry CLI is
outside HTTP admission and must not be used as an unbounded concurrent producer.
Search retains its separate two-request semaphore; sparse search can remain useful
while heavy work runs. Query encoders and model-server resident memory are not
evicted by scheduling and must be included in memory measurements.

Emit allowlisted JSON events through a shared request context. Only identifiers,
stage names, status/error codes and numeric measurements cross the logging boundary.
Persist request IDs on jobs/runs and forward them through RPC metadata. Disable raw
HTTP access logs in the application entry point because authentication callback
URLs can contain authorization codes. Operator wrappers/proxies need equivalent
redaction. Identifier-level logs still require ordinary access control and retention.

Do not introduce speculative caching or retrieval optimizations. The prior baseline
does not measure the current full workspace workload. Capture controlled baselines,
select one bottleneck and establish ranking parity before a performance change.

Backup is an offline operation after stopping writers. Keep one consistent database
snapshot open for the custom-format dump, hash immutable artifacts and compare the
source inventory after copying. Exclude browser session data. Rehearsal restore
requires an empty database named `retrievec_restore_<32 hex characters>` and a new
artifact directory separate from both the original store and bundle. Compare
ownership and saved-run fingerprints after restore. Checksums establish corruption
detection, not authenticity of an untrusted backup. Never run a dump from an
untrusted source. Do not enable artifact garbage collection in this milestone.
