CREATE TABLE IF NOT EXISTS yahoo_pickem_games (
  game_id TEXT PRIMARY KEY,
  season INTEGER NOT NULL,
  week INTEGER NOT NULL CHECK (week BETWEEN 1 AND 25),
  kickoff TIMESTAMPTZ,
  away_team TEXT NOT NULL,
  home_team TEXT NOT NULL,
  yahoo_away_pct NUMERIC(7,6) CHECK (yahoo_away_pct BETWEEN 0 AND 1),
  yahoo_home_pct NUMERIC(7,6) CHECK (yahoo_home_pct BETWEEN 0 AND 1),
  market_home_probability NUMERIC(7,6) CHECK (market_home_probability BETWEEN 0 AND 1),
  away_elo NUMERIC(10,3) NOT NULL DEFAULT 1500,
  home_elo NUMERIC(10,3) NOT NULL DEFAULT 1500,
  away_situation_points NUMERIC(8,3) NOT NULL DEFAULT 0,
  home_situation_points NUMERIC(8,3) NOT NULL DEFAULT 0,
  projected_total NUMERIC(8,3),
  source_updated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (season, week, away_team, home_team),
  CHECK (yahoo_away_pct IS NULL OR yahoo_home_pct IS NULL OR ABS((yahoo_away_pct + yahoo_home_pct) - 1.0) <= 0.02)
);
CREATE INDEX IF NOT EXISTS idx_yahoo_pickem_games_week ON yahoo_pickem_games(season, week, kickoff);

CREATE TABLE IF NOT EXISTS yahoo_pickem_predictions (
  id BIGSERIAL PRIMARY KEY,
  game_id TEXT NOT NULL REFERENCES yahoo_pickem_games(game_id) ON DELETE CASCADE,
  model_version TEXT NOT NULL,
  strategy TEXT NOT NULL,
  model_pick TEXT NOT NULL,
  model_probability NUMERIC(7,6) NOT NULL CHECK (model_probability BETWEEN 0 AND 1),
  crowd_pick TEXT NOT NULL,
  crowd_percentage NUMERIC(7,6) NOT NULL CHECK (crowd_percentage BETWEEN 0 AND 1),
  contrarian_edge NUMERIC(8,7) NOT NULL,
  signal TEXT NOT NULL,
  confidence_points INTEGER NOT NULL,
  expected_confidence_value NUMERIC(12,6) NOT NULL,
  component_json JSONB NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (game_id, model_version, strategy)
);

CREATE TABLE IF NOT EXISTS yahoo_pickem_outcomes (
  game_id TEXT PRIMARY KEY REFERENCES yahoo_pickem_games(game_id) ON DELETE CASCADE,
  winner TEXT NOT NULL,
  away_score INTEGER,
  home_score INTEGER,
  final_at TIMESTAMPTZ,
  source_url TEXT,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS yahoo_survivor_history (
  id BIGSERIAL PRIMARY KEY,
  season INTEGER NOT NULL,
  pool_key TEXT NOT NULL DEFAULT 'default',
  week INTEGER NOT NULL,
  team TEXT NOT NULL,
  result TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (season, pool_key, week),
  UNIQUE (season, pool_key, team)
);
