BEGIN;

ALTER TABLE defense_matchups
  ADD COLUMN IF NOT EXISTS version TEXT,
  ADD COLUMN IF NOT EXISTS checksum TEXT,
  ADD COLUMN IF NOT EXISTS source_recorded_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS completeness_state TEXT NOT NULL DEFAULT 'HISTORICAL',
  ADD COLUMN IF NOT EXISTS blocker TEXT,
  ADD COLUMN IF NOT EXISTS lineage JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS attribution TEXT,
  ADD COLUMN IF NOT EXISTS completed_games INTEGER;

CREATE INDEX IF NOT EXISTS defense_matchups_current_source_idx
  ON defense_matchups (season, source, completeness_state);

COMMIT;