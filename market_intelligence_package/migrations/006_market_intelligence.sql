CREATE TABLE IF NOT EXISTS market_intelligence_runs (
  id BIGSERIAL PRIMARY KEY,
  season INTEGER NOT NULL,
  week INTEGER NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'running',
  request_cost INTEGER,
  requests_remaining INTEGER,
  games_received INTEGER NOT NULL DEFAULT 0,
  games_matched INTEGER NOT NULL DEFAULT 0,
  predictions_written INTEGER NOT NULL DEFAULT 0,
  errors JSONB NOT NULL DEFAULT '[]'::jsonb,
  details JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_market_runs_week ON market_intelligence_runs(season,week,started_at DESC);

CREATE TABLE IF NOT EXISTS market_intelligence_predictions (
  game_id TEXT NOT NULL REFERENCES yahoo_pickem_games(game_id) ON DELETE CASCADE,
  model_version TEXT NOT NULL,
  strategy TEXT NOT NULL,
  model_pick TEXT NOT NULL,
  model_probability NUMERIC(7,6) NOT NULL CHECK(model_probability BETWEEN 0 AND 1),
  market_home_probability NUMERIC(7,6) NOT NULL CHECK(market_home_probability BETWEEN 0 AND 1),
  elo_home_probability NUMERIC(7,6) NOT NULL CHECK(elo_home_probability BETWEEN 0 AND 1),
  situation_home_probability NUMERIC(7,6) NOT NULL CHECK(situation_home_probability BETWEEN 0 AND 1),
  confidence_points INTEGER NOT NULL,
  expected_correct_value NUMERIC(12,6) NOT NULL,
  signal TEXT NOT NULL,
  explanation JSONB NOT NULL DEFAULT '{}'::jsonb,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY(game_id,model_version,strategy)
);

ALTER TABLE yahoo_pickem_games ADD COLUMN IF NOT EXISTS away_moneyline INTEGER;
ALTER TABLE yahoo_pickem_games ADD COLUMN IF NOT EXISTS home_moneyline INTEGER;
ALTER TABLE yahoo_pickem_games ADD COLUMN IF NOT EXISTS market_source TEXT;
ALTER TABLE yahoo_pickem_games ADD COLUMN IF NOT EXISTS market_updated_at TIMESTAMPTZ;
