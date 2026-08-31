BEGIN;
CREATE TABLE IF NOT EXISTS recommendation_history (
    id BIGSERIAL PRIMARY KEY,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    game_id TEXT NOT NULL,
    model_pick TEXT NOT NULL,
    model_probability NUMERIC(8,6) NOT NULL CHECK (model_probability BETWEEN 0 AND 1),
    crowd_pick TEXT,
    crowd_percentage NUMERIC(8,6) CHECK (crowd_percentage BETWEEN 0 AND 1),
    market_favorite TEXT,
    signal TEXT,
    explanation JSONB NOT NULL DEFAULT '{}'::jsonb,
    input_fingerprint TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (season, week, game_id, input_fingerprint)
);
CREATE TABLE IF NOT EXISTS recommendation_components (
    id BIGSERIAL PRIMARY KEY,
    recommendation_history_id BIGINT NOT NULL REFERENCES recommendation_history(id) ON DELETE CASCADE,
    component_name TEXT NOT NULL,
    component_value NUMERIC(12,8) NOT NULL,
    component_weight NUMERIC(12,8) NOT NULL,
    contribution NUMERIC(12,8) NOT NULL,
    source_timestamp TIMESTAMPTZ,
    UNIQUE (recommendation_history_id, component_name)
);
CREATE TABLE IF NOT EXISTS recommendation_changes (
    id BIGSERIAL PRIMARY KEY,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    game_id TEXT NOT NULL,
    previous_recommendation_id BIGINT REFERENCES recommendation_history(id),
    current_recommendation_id BIGINT NOT NULL REFERENCES recommendation_history(id),
    change_reason TEXT NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS intelligence_readiness_components (
    id BIGSERIAL PRIMARY KEY,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    component_name TEXT NOT NULL,
    component_score NUMERIC(8,6) NOT NULL CHECK (component_score BETWEEN 0 AND 1),
    blocker TEXT,
    warning TEXT,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (season, week, component_name)
);
CREATE INDEX IF NOT EXISTS ix_recommendation_history_week ON recommendation_history(season, week, game_id);
CREATE INDEX IF NOT EXISTS ix_recommendation_changes_week ON recommendation_changes(season, week, changed_at DESC);
COMMIT;
