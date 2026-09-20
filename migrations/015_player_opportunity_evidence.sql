BEGIN;

CREATE TABLE IF NOT EXISTS player_opportunity_evidence (
  season INTEGER NOT NULL,
  week INTEGER NOT NULL,
  player_id TEXT NOT NULL,
  team TEXT,
  position TEXT,
  opponent_team TEXT,
  targets NUMERIC(8,2),
  carries NUMERIC(8,2),
  fantasy_points_ppr NUMERIC(10,4),
  scoring_format TEXT,
  calculation_version TEXT,
  target_share NUMERIC(6,4),
  carry_share NUMERIC(6,4),
  touch_share NUMERIC(6,4),
  snap_share NUMERIC(6,4),
  route_participation NUMERIC(6,4),
  red_zone_share NUMERIC(6,4),
  role_classification TEXT,
  source TEXT,
  source_authority TEXT,
  source_recorded_at TIMESTAMPTZ,
  retrieved_at TIMESTAMPTZ,
  artifact_id TEXT,
  version TEXT,
  checksum TEXT,
  freshness_threshold_id TEXT,
  freshness_state TEXT,
  completeness_state TEXT,
  lineage JSONB NOT NULL DEFAULT '{}'::jsonb,
  publication_state TEXT,
  PRIMARY KEY (season, week, player_id)
);

ALTER TABLE player_opportunity_evidence
  ADD COLUMN IF NOT EXISTS position TEXT,
  ADD COLUMN IF NOT EXISTS opponent_team TEXT,
  ADD COLUMN IF NOT EXISTS fantasy_points_ppr NUMERIC(10,4),
  ADD COLUMN IF NOT EXISTS scoring_format TEXT,
  ADD COLUMN IF NOT EXISTS calculation_version TEXT;

CREATE INDEX IF NOT EXISTS player_opportunity_evidence_source_idx
  ON player_opportunity_evidence (season, source, completeness_state);

COMMIT;
