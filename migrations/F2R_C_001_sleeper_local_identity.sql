-- REVIEWED PROPOSAL ONLY. DO NOT APPLY AS PART OF BATCH F2R-C.
ALTER TABLE sleeper_player_map ADD COLUMN IF NOT EXISTS local_player_id INTEGER;
ALTER TABLE sleeper_player_map ADD COLUMN IF NOT EXISTS match_method TEXT;
ALTER TABLE sleeper_player_map ADD COLUMN IF NOT EXISTS match_confidence NUMERIC;
ALTER TABLE sleeper_player_map ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;
-- Foreign key and uniqueness constraints require a separate duplicate/ambiguity review.
