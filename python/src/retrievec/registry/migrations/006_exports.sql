ALTER TABLE exports ADD COLUMN IF NOT EXISTS content text;
ALTER TABLE exports ADD COLUMN IF NOT EXISTS extension text;
ALTER TABLE exports ADD COLUMN IF NOT EXISTS expires_at timestamptz NOT NULL DEFAULT clock_timestamp();
INSERT INTO schema_migrations(version) VALUES(6) ON CONFLICT DO NOTHING;
