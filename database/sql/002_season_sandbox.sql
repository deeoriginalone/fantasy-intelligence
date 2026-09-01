BEGIN;

ALTER TABLE mock_drafts
ADD COLUMN IF NOT EXISTS analysis_group VARCHAR(50);

CREATE TABLE IF NOT EXISTS application_state (
    state_key VARCHAR(100) PRIMARY KEY,
    state_value JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recommendation_history (
    id SERIAL PRIMARY KEY,
    data_mode VARCHAR(20) NOT NULL,
    sandbox_draft_id INTEGER,
    recommendation_type VARCHAR(40) NOT NULL,
    subject VARCHAR(255),
    action VARCHAR(255),
    score NUMERIC(10,2),
    confidence VARCHAR(20),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(25) NOT NULL DEFAULT 'proposed',
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS recommendation_history_context_idx
ON recommendation_history (
    data_mode,
    sandbox_draft_id,
    recommendation_type,
    created_at DESC
);

COMMIT;
