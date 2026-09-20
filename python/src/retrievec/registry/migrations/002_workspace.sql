ALTER TABLE collections ADD COLUMN IF NOT EXISTS title text NOT NULL DEFAULT 'Untitled collection';
ALTER TABLE collections ADD COLUMN IF NOT EXISTS archived boolean NOT NULL DEFAULT false;
ALTER TABLE collections DROP CONSTRAINT IF EXISTS collections_visibility_check;
ALTER TABLE collections ADD CONSTRAINT collections_visibility_check CHECK(visibility IN ('private','curated'));
CREATE TABLE IF NOT EXISTS identities (
 issuer text NOT NULL, subject text NOT NULL, principal_id text NOT NULL REFERENCES principals,
 PRIMARY KEY(issuer,subject), UNIQUE(principal_id)
);
CREATE TABLE IF NOT EXISTS browser_sessions (
 token_hash text PRIMARY KEY, data jsonb NOT NULL, expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS browser_sessions_expiry ON browser_sessions(expires_at);
CREATE TABLE IF NOT EXISTS upload_sources (
 source_id uuid PRIMARY KEY, collection_id text NOT NULL REFERENCES collections,
 owner_id text NOT NULL REFERENCES principals, storage_key text NOT NULL,
 display_name text NOT NULL, media_type text NOT NULL, size_bytes bigint NOT NULL CHECK(size_bytes>0),
 source_hash text NOT NULL, paper_id text NOT NULL,
 job_id uuid REFERENCES ingestion_jobs, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS upload_collection ON upload_sources(collection_id);
CREATE TABLE IF NOT EXISTS conversations (
 conversation_id uuid PRIMARY KEY, owner_id text NOT NULL REFERENCES principals,
 collection_id text NOT NULL REFERENCES collections, title text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS research_runs (
 run_id uuid PRIMARY KEY, conversation_id uuid NOT NULL REFERENCES conversations,
 owner_id text NOT NULL REFERENCES principals, collection_id text NOT NULL REFERENCES collections,
 snapshot_id text NOT NULL, original_question text NOT NULL, effective_query text NOT NULL,
 configuration jsonb NOT NULL, state text NOT NULL,
 FOREIGN KEY(collection_id,snapshot_id) REFERENCES retrieval_snapshots(collection_id,snapshot_id)
);
CREATE TABLE IF NOT EXISTS evidence_citations (
 citation_id uuid PRIMARY KEY, run_id uuid NOT NULL REFERENCES research_runs,
 chunk_id text NOT NULL, evidence jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS exports (
 export_id uuid PRIMARY KEY, run_id uuid NOT NULL REFERENCES research_runs,
 storage_key text NOT NULL, media_type text NOT NULL
);
INSERT INTO schema_migrations(version) VALUES(2) ON CONFLICT DO NOTHING;
