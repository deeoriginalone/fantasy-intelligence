BEGIN;
CREATE TABLE IF NOT EXISTS weekly_operations_runs (
    id SERIAL PRIMARY KEY,
    data_mode VARCHAR(20) NOT NULL,
    sandbox_draft_id INTEGER,
    operation_type VARCHAR(40) NOT NULL,
    week INTEGER,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS weekly_operations_runs_context_idx
ON weekly_operations_runs (data_mode, sandbox_draft_id, operation_type, created_at DESC);
COMMIT;
