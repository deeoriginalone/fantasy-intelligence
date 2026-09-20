BEGIN;

CREATE TABLE IF NOT EXISTS snap_share_evidence (
  season INTEGER NOT NULL,
  week INTEGER NOT NULL,
  player_id TEXT NOT NULL,
  pfr_player_id TEXT NOT NULL,
  team TEXT NOT NULL,
  opponent_team TEXT,
  snap_share NUMERIC(8,6),
  source TEXT NOT NULL,
  source_authority TEXT NOT NULL,
  source_recorded_at TIMESTAMPTZ,
  retrieved_at TIMESTAMPTZ NOT NULL,
  artifact_id TEXT NOT NULL,
  version TEXT NOT NULL,
  checksum TEXT NOT NULL,
  freshness_threshold_id TEXT NOT NULL,
  freshness_state TEXT NOT NULL,
  completeness_state TEXT NOT NULL,
  lineage JSONB NOT NULL DEFAULT '{}'::jsonb,
  publication_state TEXT NOT NULL,
  PRIMARY KEY (season, week, player_id)
);

CREATE INDEX IF NOT EXISTS snap_share_evidence_lookup_idx
  ON snap_share_evidence (player_id, season, week DESC);

COMMIT;
