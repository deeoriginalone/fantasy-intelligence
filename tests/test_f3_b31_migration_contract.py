from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_007 = ROOT / "migrations/007_draft_event_pipeline.sql"
MIGRATION_010 = ROOT / "migrations/010_draft_event_pipeline_upgrade.sql"


def test_clean_install_keeps_event_log_unconstrained_and_selection_state_unique():
    sql = MIGRATION_007.read_text(encoding="utf-8")
    event_log, selection_state = sql.split(
        "CREATE TABLE IF NOT EXISTS draft_selections", 1
    )

    assert "UNIQUE (draft_id, pick_number)" not in event_log
    assert "UNIQUE (draft_id, player_id)" not in event_log
    assert "PRIMARY KEY (draft_id, pick_number)" in sql
    assert "UNIQUE (draft_id, player_id)" in selection_state
    assert "event_id TEXT PRIMARY KEY" in sql


def test_upgrade_drops_only_obsolete_event_log_constraints_idempotently():
    sql = MIGRATION_010.read_text(encoding="utf-8")

    assert sql.startswith("BEGIN;")
    assert "DROP CONSTRAINT IF EXISTS draft_events_draft_id_pick_number_key" in sql
    assert "DROP CONSTRAINT IF EXISTS draft_events_draft_id_player_id_key" in sql
    assert sql.rstrip().endswith("COMMIT;")
    assert "DELETE FROM" not in sql
    assert "draft_selections" in sql
    assert "applied-state uniqueness boundary" in sql