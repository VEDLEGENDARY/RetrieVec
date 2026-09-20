CREATE TABLE IF NOT EXISTS schema_migrations(version integer PRIMARY KEY);
CREATE TABLE IF NOT EXISTS principals (
 principal_id text PRIMARY KEY CHECK (length(principal_id)>0)
);
CREATE TABLE IF NOT EXISTS collections (
 collection_id text PRIMARY KEY CHECK (length(collection_id)>0),
 owner_id text NOT NULL REFERENCES principals,
 visibility text NOT NULL DEFAULT 'private' CHECK(visibility='private'),
 active_snapshot text
);
CREATE TABLE IF NOT EXISTS paper_versions (
 paper_version_id text PRIMARY KEY, paper_id text NOT NULL,
 source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[0-9a-f]{64}$'),
 provenance jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS collection_papers (
 collection_id text NOT NULL REFERENCES collections,
 paper_id text NOT NULL, paper_version_id text NOT NULL REFERENCES paper_versions,
 PRIMARY KEY(collection_id,paper_id)
);
CREATE TABLE IF NOT EXISTS retrieval_snapshots (
 snapshot_id text PRIMARY KEY CHECK(snapshot_id ~ '^rs_[0-9a-f]{64}$'),
 collection_id text NOT NULL REFERENCES collections,
 corpus_snapshot_id text NOT NULL CHECK(corpus_snapshot_id ~ '^ss_[0-9a-f]{64}$'),
 manifest jsonb NOT NULL,
 state text NOT NULL CHECK(state IN ('prepared','ready')),
 capabilities text[] NOT NULL,
 UNIQUE(collection_id,snapshot_id)
);
DO $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conname='collection_active_snapshot_fk'
               AND conrelid='collections'::regclass) THEN
 ALTER TABLE collections ADD CONSTRAINT collection_active_snapshot_fk
 FOREIGN KEY(collection_id,active_snapshot) REFERENCES retrieval_snapshots(collection_id,snapshot_id);
 END IF;
END $$;
CREATE TABLE IF NOT EXISTS ingestion_jobs (
 job_id uuid PRIMARY KEY,
 collection_id text NOT NULL REFERENCES collections,
 idempotency_key text NOT NULL CHECK(length(idempotency_key)>0),
 input_hash text NOT NULL, config_hash text NOT NULL,
 payload jsonb NOT NULL,
 state text NOT NULL DEFAULT 'queued' CHECK(state IN ('queued','running','retry_wait','succeeded','failed','cancelled')),
 stage text NOT NULL DEFAULT 'queued', progress jsonb NOT NULL DEFAULT '{}',
 attempts integer NOT NULL DEFAULT 0 CHECK(attempts>=0),
 max_attempts integer NOT NULL DEFAULT 3 CHECK(max_attempts BETWEEN 1 AND 10),
 fencing_token bigint NOT NULL DEFAULT 0,
 lease_until timestamptz, available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 expected_parent text, output_snapshot text,
 error_code text,
 UNIQUE(collection_id,idempotency_key),
 FOREIGN KEY(collection_id,expected_parent) REFERENCES retrieval_snapshots(collection_id,snapshot_id),
 FOREIGN KEY(collection_id,output_snapshot) REFERENCES retrieval_snapshots(collection_id,snapshot_id)
);
CREATE INDEX IF NOT EXISTS jobs_claim_idx ON ingestion_jobs(state,available_at,lease_until);
CREATE TABLE IF NOT EXISTS experiment_runs (
 run_id text PRIMARY KEY, collection_id text NOT NULL REFERENCES collections,
 snapshot_id text NOT NULL, query_hash text NOT NULL, config_hash text NOT NULL,
 dataset_hash text, status text NOT NULL CHECK(status IN ('running','succeeded','failed')),
 artifact_reference text NOT NULL,
 FOREIGN KEY(collection_id,snapshot_id) REFERENCES retrieval_snapshots(collection_id,snapshot_id)
);
INSERT INTO schema_migrations(version) VALUES(1) ON CONFLICT DO NOTHING;
