# Snapshot authority, storage and RPC

Corpus IDs (ss_), retrieval IDs (rs_), embedding IDs (em_) and run identities are
distinct. Content hashes exclude timestamps. Storage paths are derived only from
validated hashes: corpora/<ss_...>, segments/<hash>.seg,
snapshots/<rs_...>/manifest.json, embeddings/<em_...>.

PostgreSQL 18 is the sole active-pointer authority. Prepared snapshots become
ready only after all declared sparse/dense artifacts validate; collection activation
uses expected-parent CAS. Jobs use database time, SKIP LOCKED claims, bounded
attempts and monotonically increasing fencing tokens. Stale workers cannot update
progress or activate. Recovery reconciles a previously successful activation.
See [PostgreSQL locking](https://www.postgresql.org/docs/18/sql-select.html) and
[database time](https://www.postgresql.org/docs/18/functions-datetime.html).

Python resolves owner/collection and pins one retrieval snapshot for sparse RPC,
dense search and passage reads. Go independently checks registry ownership and
snapshot state. Distinct local reader/worker bearer credentials are configured
outside Git; control RPC requires the worker credential. Loopback is required for
unencrypted development transport. Cross-host transport must use TLS.

Generated Protobuf clients share Search, GetSnapshotInfo and PrepareSnapshot.
Preparation never changes the database active pointer. Search adapters use one
reader interface with aggregate snapshot statistics. Empty collections have zero
segments. Old snapshots remain available for saved runs and in-flight requests.

Files are flushed before immutable publication. Database and filesystem publication
are explicitly separate stages. Process-interruption tests establish recovery,
not power-loss durability; no cross-filesystem atomicity or universal Windows
directory-fsync guarantee is claimed.
