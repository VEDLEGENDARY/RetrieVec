ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT clock_timestamp();
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS idempotency_key text;
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS request_hash text;
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS parent_run uuid REFERENCES research_runs;
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS result jsonb;
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS error_code text;
CREATE UNIQUE INDEX IF NOT EXISTS research_idempotency ON research_runs(owner_id,conversation_id,idempotency_key);
CREATE INDEX IF NOT EXISTS research_history ON research_runs(conversation_id,created_at);
INSERT INTO schema_migrations(version) VALUES(3) ON CONFLICT DO NOTHING;
