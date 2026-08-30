ALTER TABLE draft_decision_outcomes ADD COLUMN IF NOT EXISTS outcome_status VARCHAR(20) NOT NULL DEFAULT 'PENDING';
ALTER TABLE draft_decision_outcomes ADD COLUMN IF NOT EXISTS model_version VARCHAR(50) DEFAULT 'v1.7';
ALTER TABLE draft_decision_outcomes ADD COLUMN IF NOT EXISTS source_freshness JSONB;
UPDATE draft_decision_outcomes SET outcome_status=CASE WHEN actual_available IS TRUE THEN 'AVAILABLE' WHEN actual_available IS FALSE THEN 'GONE' ELSE 'PENDING' END;
CREATE INDEX IF NOT EXISTS idx_draft_outcome_status ON draft_decision_outcomes(draft_id,outcome_status,next_pick);
