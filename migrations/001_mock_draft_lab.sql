BEGIN;

ALTER TABLE league_info
    ADD COLUMN IF NOT EXISTS team_count INTEGER DEFAULT 10;


CREATE TABLE IF NOT EXISTS mock_drafts (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    league_size INTEGER NOT NULL CHECK (league_size BETWEEN 2 AND 20),
    rounds INTEGER NOT NULL CHECK (rounds BETWEEN 1 AND 30),
    user_draft_slot INTEGER NOT NULL,
    user_strategy VARCHAR(30) NOT NULL,
    seed BIGINT,
    user_roster_score NUMERIC(10,2),
    user_draft_grade NUMERIC(6,2),
    status VARCHAR(20) NOT NULL DEFAULT 'complete'
);

CREATE TABLE IF NOT EXISTS mock_picks (
    id BIGSERIAL PRIMARY KEY,
    draft_id BIGINT NOT NULL REFERENCES mock_drafts(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    overall_pick INTEGER NOT NULL,
    team_slot INTEGER NOT NULL,
    player_id BIGINT REFERENCES players(id),
    player_name TEXT NOT NULL,
    position VARCHAR(10) NOT NULL,
    strategy VARCHAR(30) NOT NULL,
    value_score NUMERIC(10,3),
    UNIQUE (draft_id, overall_pick),
    UNIQUE (draft_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_mock_picks_draft ON mock_picks(draft_id);
CREATE INDEX IF NOT EXISTS idx_mock_picks_player ON mock_picks(player_id);
CREATE INDEX IF NOT EXISTS idx_mock_drafts_created ON mock_drafts(created_at DESC);

COMMIT;
