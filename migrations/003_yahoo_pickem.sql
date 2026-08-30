PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS yahoo_pickem_games (
  game_id TEXT PRIMARY KEY,
  season INTEGER NOT NULL,
  week INTEGER NOT NULL CHECK (week BETWEEN 1 AND 25),
  kickoff TEXT NOT NULL,
  away_team TEXT NOT NULL,
  home_team TEXT NOT NULL,
  yahoo_away_pct REAL NOT NULL CHECK (yahoo_away_pct BETWEEN 0 AND 1),
  yahoo_home_pct REAL NOT NULL CHECK (yahoo_home_pct BETWEEN 0 AND 1),
  market_home_probability REAL NOT NULL CHECK (market_home_probability BETWEEN 0 AND 1),
  away_elo REAL NOT NULL DEFAULT 1500,
  home_elo REAL NOT NULL DEFAULT 1500,
  away_situation_points REAL NOT NULL DEFAULT 0,
  home_situation_points REAL NOT NULL DEFAULT 0,
  projected_total REAL,
  source_updated_at TEXT,
  raw_payload TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (season, week, away_team, home_team)
);
CREATE INDEX IF NOT EXISTS idx_pickem_games_week ON yahoo_pickem_games(season, week, kickoff);

CREATE TABLE IF NOT EXISTS yahoo_pickem_predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_id TEXT NOT NULL REFERENCES yahoo_pickem_games(game_id) ON DELETE CASCADE,
  model_version TEXT NOT NULL,
  strategy TEXT NOT NULL,
  model_pick TEXT NOT NULL,
  model_probability REAL NOT NULL CHECK (model_probability BETWEEN 0 AND 1),
  crowd_pick TEXT NOT NULL,
  crowd_percentage REAL NOT NULL CHECK (crowd_percentage BETWEEN 0 AND 1),
  contrarian_edge REAL NOT NULL,
  signal TEXT NOT NULL,
  confidence_points INTEGER NOT NULL,
  expected_confidence_value REAL NOT NULL,
  component_json TEXT NOT NULL,
  generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (game_id, model_version, strategy)
);

CREATE TABLE IF NOT EXISTS yahoo_pickem_outcomes (
  game_id TEXT PRIMARY KEY REFERENCES yahoo_pickem_games(game_id) ON DELETE CASCADE,
  winner TEXT NOT NULL,
  away_score INTEGER,
  home_score INTEGER,
  final_at TEXT,
  source_url TEXT,
  recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS yahoo_survivor_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  season INTEGER NOT NULL,
  pool_key TEXT NOT NULL DEFAULT 'default',
  week INTEGER NOT NULL,
  team TEXT NOT NULL,
  result TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (season, pool_key, week),
  UNIQUE (season, pool_key, team)
);
