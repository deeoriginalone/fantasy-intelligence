BEGIN;

CREATE TABLE IF NOT EXISTS model_only_elo_source_observations (
  id BIGSERIAL PRIMARY KEY,
  domain TEXT NOT NULL DEFAULT 'model_only_future_elo',
  source_identifier TEXT NOT NULL,
  source_url TEXT NOT NULL,
  retrieved_at TIMESTAMPTZ NOT NULL,
  source_recorded_at TIMESTAMPTZ,
  source_recorded_at_available BOOLEAN NOT NULL,
  source_checksum TEXT,
  etag TEXT,
  content_length_header TEXT,
  content_length_actual BIGINT,
  http_status INTEGER,
  changed_from_previous BOOLEAN,
  previous_checksum TEXT,
  previous_retrieved_at TIMESTAMPTZ,
  observation_state TEXT NOT NULL,
  blocker_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Append-only: no UPDATE/DELETE is ever issued against this table by application code.
CREATE INDEX IF NOT EXISTS ix_model_only_elo_source_observations_lookup
  ON model_only_elo_source_observations (source_identifier, retrieved_at DESC);

COMMIT;
