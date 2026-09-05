BEGIN;

CREATE TABLE IF NOT EXISTS draft_events (
    event_id TEXT PRIMARY KEY,
    league_id TEXT NOT NULL,
    draft_id TEXT NOT NULL,
    pick_number INTEGER NOT NULL CHECK (pick_number > 0),
    round INTEGER NOT NULL CHECK (round > 0),
    round_pick INTEGER NOT NULL CHECK (round_pick > 0),
    roster_id TEXT,
    owner_id TEXT,
    player_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('selection')),
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    processing_status TEXT NOT NULL DEFAULT 'RECEIVED'
        CHECK (processing_status IN ('RECEIVED','VALIDATED','APPLIED','FAILED')),
    validation_error TEXT,
    processed_at TIMESTAMPTZ,
    CHECK (roster_id IS NOT NULL OR owner_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS draft_selections (
    draft_id TEXT NOT NULL,
    league_id TEXT NOT NULL,
    pick_number INTEGER NOT NULL CHECK (pick_number > 0),
    round INTEGER NOT NULL CHECK (round > 0),
    round_pick INTEGER NOT NULL CHECK (round_pick > 0),
    roster_id TEXT,
    owner_id TEXT,
    player_id TEXT NOT NULL,
    source_event_id TEXT NOT NULL REFERENCES draft_events(event_id),
    selected_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (draft_id, pick_number),
    UNIQUE (draft_id, player_id),
    CHECK (roster_id IS NOT NULL OR owner_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_draft_events_status ON draft_events(processing_status);
CREATE INDEX IF NOT EXISTS idx_draft_events_draft_order ON draft_events(draft_id, pick_number);
CREATE INDEX IF NOT EXISTS idx_draft_selections_owner ON draft_selections(draft_id, roster_id, owner_id);

COMMIT;
