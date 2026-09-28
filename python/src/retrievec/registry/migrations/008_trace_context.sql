SET LOCAL lock_timeout = '3s';
ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS traceparent varchar(55);
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS traceparent varchar(55);
INSERT INTO schema_migrations(version) VALUES(8) ON CONFLICT DO NOTHING;
