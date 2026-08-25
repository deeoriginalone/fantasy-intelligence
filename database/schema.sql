CREATE TABLE league_settings (
    id SERIAL PRIMARY KEY,
    league_name TEXT,
    team_count INT,
    scoring_type TEXT,
    draft_date TIMESTAMP
);

CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    yahoo_id TEXT,
    player_name TEXT,
    position TEXT,
    team TEXT
);

CREATE TABLE rankings (
    id SERIAL PRIMARY KEY,
    player_id INT,
    ranking INT,
    tier INT,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agent_reports (
    id SERIAL PRIMARY KEY,
    agent_name TEXT,
    report_type TEXT,
    content JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
