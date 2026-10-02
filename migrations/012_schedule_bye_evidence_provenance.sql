BEGIN;

ALTER TABLE nfl_schedule
  ADD COLUMN IF NOT EXISTS source VARCHAR(255),
  ADD COLUMN IF NOT EXISTS source_recorded_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS retrieved_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;

ALTER TABLE bye_weeks
  ADD COLUMN IF NOT EXISTS source_recorded_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS retrieved_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS nfl_schedule_source_season_idx
  ON nfl_schedule (season, source);

CREATE INDEX IF NOT EXISTS bye_weeks_source_season_idx
  ON bye_weeks (season, source);

COMMIT;
