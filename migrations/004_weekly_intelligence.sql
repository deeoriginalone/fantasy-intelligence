BEGIN;
CREATE TABLE IF NOT EXISTS nfl_teams (
  team_abbr VARCHAR(5) PRIMARY KEY,
  team_name VARCHAR(80) UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS nfl_schedule (
  season INTEGER NOT NULL,
  week INTEGER NOT NULL,
  match_number INTEGER NOT NULL,
  game_time_utc TIMESTAMPTZ NOT NULL,
  game_time_pacific TIMESTAMP NOT NULL,
  location VARCHAR(150),
  home_team VARCHAR(5) NOT NULL REFERENCES nfl_teams(team_abbr),
  away_team VARCHAR(5) NOT NULL REFERENCES nfl_teams(team_abbr),
  result VARCHAR(80),
  PRIMARY KEY (season, match_number)
);
CREATE INDEX IF NOT EXISTS nfl_schedule_team_week_idx ON nfl_schedule(season, week, home_team, away_team);
CREATE TABLE IF NOT EXISTS bye_weeks (
  season INTEGER NOT NULL,
  team VARCHAR(5) NOT NULL REFERENCES nfl_teams(team_abbr),
  bye_week INTEGER NOT NULL,
  source VARCHAR(255),
  PRIMARY KEY (season, team)
);
CREATE TABLE IF NOT EXISTS injury_reports (
  season INTEGER NOT NULL,
  report_date DATE NOT NULL,
  player_name VARCHAR(150) NOT NULL,
  team VARCHAR(5),
  position VARCHAR(10),
  injury VARCHAR(120),
  status VARCHAR(40),
  estimated_return VARCHAR(120),
  PRIMARY KEY (season, report_date, player_name)
);
CREATE INDEX IF NOT EXISTS injury_reports_player_idx ON injury_reports(player_name, report_date DESC);
CREATE TABLE IF NOT EXISTS defense_matchups (
  season INTEGER NOT NULL,
  position VARCHAR(5) NOT NULL,
  defense_team VARCHAR(5) NOT NULL,
  defense_rank INTEGER NOT NULL,
  fp_per_game_allowed NUMERIC(8,2) NOT NULL,
  source VARCHAR(255),
  PRIMARY KEY (season, position, defense_team)
);
CREATE TABLE IF NOT EXISTS weekly_intelligence_runs (
  id SERIAL PRIMARY KEY,
  season INTEGER NOT NULL,
  week INTEGER NOT NULL,
  source_files JSONB NOT NULL DEFAULT '{}'::jsonb,
  imported_at TIMESTAMP NOT NULL DEFAULT NOW()
);
COMMIT;
