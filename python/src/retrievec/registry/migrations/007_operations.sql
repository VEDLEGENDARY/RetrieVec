ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS request_id text;
ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT clock_timestamp();
ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS stage_started_at timestamptz NOT NULL DEFAULT clock_timestamp();
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS request_id text;
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS stage_started_at timestamptz NOT NULL DEFAULT clock_timestamp();
INSERT INTO schema_migrations(version) VALUES(7) ON CONFLICT DO NOTHING;
