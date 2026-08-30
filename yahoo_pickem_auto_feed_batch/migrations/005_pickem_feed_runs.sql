CREATE TABLE IF NOT EXISTS pickem_feed_runs (
  id BIGSERIAL PRIMARY KEY,
  season INTEGER NOT NULL,
  week INTEGER NOT NULL,
  provider TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'running',
  games_received INTEGER NOT NULL DEFAULT 0,
  games_updated INTEGER NOT NULL DEFAULT 0,
  errors JSONB NOT NULL DEFAULT '[]'::jsonb,
  details JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_pickem_feed_runs_week ON pickem_feed_runs(season,week,started_at DESC);

ALTER TABLE yahoo_pickem_games ADD COLUMN IF NOT EXISTS crowd_source TEXT;
ALTER TABLE yahoo_pickem_games ADD COLUMN IF NOT EXISTS market_source TEXT;
ALTER TABLE yahoo_pickem_games ADD COLUMN IF NOT EXISTS crowd_updated_at TIMESTAMPTZ;
ALTER TABLE yahoo_pickem_games ADD COLUMN IF NOT EXISTS market_updated_at TIMESTAMPTZ;
ALTER TABLE yahoo_pickem_games ADD COLUMN IF NOT EXISTS away_moneyline INTEGER;
ALTER TABLE yahoo_pickem_games ADD COLUMN IF NOT EXISTS home_moneyline INTEGER;
