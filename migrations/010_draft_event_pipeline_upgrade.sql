BEGIN;

-- draft_events is the audit log: conflicting events must remain recordable and
-- can be marked FAILED; draft_selections is the applied-state uniqueness boundary.
ALTER TABLE draft_events
    DROP CONSTRAINT IF EXISTS draft_events_draft_id_pick_number_key,
    DROP CONSTRAINT IF EXISTS draft_events_draft_id_player_id_key;

COMMIT;