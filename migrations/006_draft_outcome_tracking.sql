CREATE TABLE IF NOT EXISTS draft_decision_outcomes (
 id BIGSERIAL PRIMARY KEY,
 league_id VARCHAR(50) NOT NULL,
 draft_id VARCHAR(50) NOT NULL,
 decision_pick INTEGER NOT NULL,
 next_pick INTEGER NOT NULL,
 player_name TEXT NOT NULL,
 player_id VARCHAR(50),
 position VARCHAR(10),
 decision VARCHAR(30),
 confidence NUMERIC(6,2),
 reconciled_pct NUMERIC(6,2),
 monte_carlo_pct NUMERIC(6,2),
 opponent_pct NUMERIC(6,2),
 survival_pct NUMERIC(6,2),
 expected_value_loss NUMERIC(10,2),
 actual_available BOOLEAN,
 resolved_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(draft_id, decision_pick, player_name)
);
CREATE INDEX IF NOT EXISTS idx_draft_outcomes_pending ON draft_decision_outcomes(draft_id,next_pick) WHERE actual_available IS NULL;
CREATE INDEX IF NOT EXISTS idx_draft_outcomes_recent ON draft_decision_outcomes(created_at DESC);
