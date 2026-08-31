BEGIN;
CREATE TABLE IF NOT EXISTS ingestion_runs(
 run_id UUID PRIMARY KEY, source_name TEXT NOT NULL, season INTEGER NOT NULL, week INTEGER NOT NULL,
 file_name TEXT NOT NULL, status TEXT NOT NULL, accepted_count INTEGER NOT NULL DEFAULT 0,
 rejected_count INTEGER NOT NULL DEFAULT 0, started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), finished_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS ingestion_records(
 id BIGSERIAL PRIMARY KEY, run_id UUID NOT NULL REFERENCES ingestion_runs(run_id), source_name TEXT NOT NULL,
 season INTEGER NOT NULL, week INTEGER NOT NULL, record_key TEXT NOT NULL, payload JSONB NOT NULL,
 ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(source_name,season,week,record_key)
);
CREATE INDEX IF NOT EXISTS ix_ingestion_records_week ON ingestion_records(season,week,source_name);
COMMIT;
