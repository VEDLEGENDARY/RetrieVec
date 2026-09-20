ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS fencing_token bigint NOT NULL DEFAULT 0;
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS lease_until timestamptz;
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS event_sequence bigint NOT NULL DEFAULT 0;
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS attempts integer NOT NULL DEFAULT 0;
CREATE TABLE IF NOT EXISTS run_events (
 run_id uuid NOT NULL REFERENCES research_runs, event_id bigint NOT NULL,
 type text NOT NULL, payload jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY(run_id,event_id)
);
INSERT INTO schema_migrations(version) VALUES(5) ON CONFLICT DO NOTHING;
