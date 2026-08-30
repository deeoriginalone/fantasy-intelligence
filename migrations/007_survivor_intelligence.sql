CREATE TABLE IF NOT EXISTS survivor_pools (
  pool_key TEXT PRIMARY KEY,
  pool_name TEXT NOT NULL,
  season INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS survivor_selections (
  id BIGSERIAL PRIMARY KEY,
  pool_key TEXT NOT NULL REFERENCES survivor_pools(pool_key) ON DELETE CASCADE,
  season INTEGER NOT NULL,
  week INTEGER NOT NULL CHECK (week BETWEEN 1 AND 25),
  team TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','won','lost','void')),
  model_probability NUMERIC(7,6),
  survivor_score NUMERIC(7,6),
  notes TEXT,
  selected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(pool_key,season,week),
  UNIQUE(pool_key,season,team)
);
CREATE INDEX IF NOT EXISTS idx_survivor_selections_pool ON survivor_selections(pool_key,season,week);

CREATE TABLE IF NOT EXISTS survivor_recommendation_runs (
  id BIGSERIAL PRIMARY KEY,
  pool_key TEXT NOT NULL,
  season INTEGER NOT NULL,
  week INTEGER NOT NULL,
  strategy TEXT NOT NULL,
  primary_team TEXT,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  details JSONB NOT NULL DEFAULT '{}'::jsonb
);
