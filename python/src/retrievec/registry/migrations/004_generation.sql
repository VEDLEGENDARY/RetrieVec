CREATE TABLE IF NOT EXISTS provider_consents (
 collection_id text NOT NULL REFERENCES collections, provider_hash text NOT NULL,
 granted_by text NOT NULL REFERENCES principals, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(collection_id,provider_hash)
);
INSERT INTO schema_migrations(version) VALUES(4) ON CONFLICT DO NOTHING;
