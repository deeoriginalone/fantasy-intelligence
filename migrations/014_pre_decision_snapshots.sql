BEGIN;

CREATE TABLE IF NOT EXISTS pre_decision_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    decision_type TEXT NOT NULL,
    decision_subject TEXT NOT NULL,
    entity_identity JSONB,
    decision_output JSONB,
    evidence_state TEXT NOT NULL,
    evidence_source JSONB,
    evidence_lineage JSONB,
    source_recorded_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ,
    freshness_state TEXT NOT NULL,
    completeness_state TEXT NOT NULL,
    confidence JSONB,
    blockers JSONB NOT NULL DEFAULT '[]'::jsonb,
    captured_at TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL,
    decision_effect TEXT NOT NULL CHECK (decision_effect = 'NONE'),
    snapshot_payload JSONB NOT NULL,
    CHECK (evidence_state IN ('AVAILABLE', 'UNAVAILABLE', 'BLOCKED', 'STALE', 'INSUFFICIENT_EVIDENCE')),
    CHECK (freshness_state IN ('FRESH', 'AGING', 'STALE', 'UNAVAILABLE', 'BLOCKED')),
    CHECK (completeness_state IN ('COMPLETE', 'INCOMPLETE', 'UNAVAILABLE'))
);

CREATE INDEX IF NOT EXISTS pre_decision_snapshots_subject_idx
    ON pre_decision_snapshots (season, week, decision_type, decision_subject, captured_at DESC);

CREATE OR REPLACE FUNCTION reject_pre_decision_snapshot_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'pre-decision snapshots are append-only';
END;
$$;

DROP TRIGGER IF EXISTS pre_decision_snapshots_immutable ON pre_decision_snapshots;
CREATE TRIGGER pre_decision_snapshots_immutable
BEFORE UPDATE OR DELETE ON pre_decision_snapshots
FOR EACH ROW EXECUTE FUNCTION reject_pre_decision_snapshot_mutation();

COMMIT;
