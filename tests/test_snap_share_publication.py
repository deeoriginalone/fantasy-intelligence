import json
import pytest
from pathlib import Path

from services.snap_share_publication import publish_snap_share
from services.snap_share_reader import read_snap_share


class Cursor:
    description = []
    def __init__(self, rows=None, fail_on_insert=False): self.rows = rows or []; self.statements = []; self.fail_on_insert = fail_on_insert
    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        if self.fail_on_insert and sql.strip().startswith("INSERT"):
            raise RuntimeError("SIMULATED_SNAP_PUBLICATION_FAILURE")
    def fetchall(self): return self.rows
    def close(self): pass


class Connection:
    def __init__(self, rows=None, fail_on_insert=False): self.cursor_obj = Cursor(rows, fail_on_insert); self.committed = False; self.rolled_back = False
    def cursor(self): return self.cursor_obj
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True


def evidence():
    return {
        "season": 2026,
        "freshness_state": "FRESH",
        "rows": [{"season": 2026, "week": 1, "gsis_id": "gsis-1", "pfr_player_id": "pfr-1", "team": "KC", "opponent": "DEN", "snap_share": 0.75, "authoritative": True}],
        "reconciliation": {"reconciled": True, "duplicate_count": 0, "contradictory_count": 0, "unresolved_identity_count": 0, "ambiguous_identity_count": 0, "contradictory_identity_count": 0},
        "provenance": {"source": "automated:nflverse", "source_authority": "automated", "retrieved_at": "2026-09-20T12:00:00+00:00", "source_recorded_at": "2026-09-19T12:00:00+00:00", "artifact_identifier": "snap_counts", "version": "snap_counts_2026", "checksum": "sha256:test", "freshness_threshold_id": "snap_share.evidence.v1", "identity_crosswalk": {"source": "https://nflverse.example/players.csv.gz", "source_authority": "automated:nflverse", "artifact_id": "nflverse.players.csv", "version": "players-v1", "checksum": "sha256:players", "source_recorded_at": "2026-09-19T12:00:00+00:00", "retrieved_at": "2026-09-20T12:00:00+00:00"}},
    }


def test_publication_writes_dedicated_snap_share_table_atomically():
    conn = Connection()
    assert publish_snap_share(conn, evidence()) == 1
    assert conn.committed
    sql = conn.cursor_obj.statements[1][0]
    assert "snap_share_evidence" in sql
    assert "PUBLISHED" in conn.cursor_obj.statements[1][1]
    assert "identity_crosswalk" in conn.cursor_obj.statements[1][1][-2]


def test_publication_fails_closed_for_missing_threshold_state():
    blocked = dict(evidence(), freshness_state="UNAVAILABLE")
    with pytest.raises(ValueError, match="SNAP_SHARE_FRESHNESS_UNAVAILABLE"):
        publish_snap_share(Connection(), blocked)


def test_publication_filters_unresolved_rows_and_keeps_completed_week_scope():
    data = evidence()
    data["weeks"] = [1, 2, 3]
    data["rows"].append({"season": 2026, "week": 1, "gsis_id": None, "pfr_player_id": "pfr-unmapped", "snap_share": 0.5, "authoritative": False})
    conn = Connection()

    assert publish_snap_share(conn, data) == 1
    delete_sql, delete_params = conn.cursor_obj.statements[0]
    assert "source='automated:nflverse'" in delete_sql
    assert delete_params == (2026, [1, 2, 3])
    assert sum(sql.strip().startswith("INSERT") for sql, _ in conn.cursor_obj.statements) == 1


def test_publication_blocks_invalid_share_and_contradictory_batch():
    invalid = evidence()
    invalid["rows"][0]["snap_share"] = 1.01
    with pytest.raises(ValueError, match="SNAP_SHARE_ROW_INVALID"):
        publish_snap_share(Connection(), invalid)

    contradictory = evidence()
    contradictory["reconciliation"]["contradictory_count"] = 2
    with pytest.raises(ValueError, match="SNAP_SHARE_CONTRADICTORY_PLAYER_WEEK"):
        publish_snap_share(Connection(), contradictory)


def test_publication_rolls_back_on_transaction_failure():
    conn = Connection(fail_on_insert=True)
    with pytest.raises(RuntimeError, match="SIMULATED_SNAP_PUBLICATION_FAILURE"):
        publish_snap_share(conn, evidence())
    assert not conn.committed
    assert conn.rolled_back


def test_reader_returns_published_snap_share_newest_first():
    lineage = json.dumps({"sample": {"position": "WR", "participation_domain": "OFFENSE", "snap_count": 52, "percentage_field": "offense_pct"}})
    rows = [(2026, 2, "gsis-1", "pfr-1", "KC", "DEN", 0.5, "automated:nflverse", "automated", "2026-09-19", "2026-09-20", "snap_counts", "snap_counts_2026", "sha256:test", "snap_share.evidence.v1", "FRESH", "COMPLETE", lineage, "PUBLISHED")]
    result = read_snap_share(Connection(rows), player_id="gsis-1", season=2026)
    assert result["state"] == "AVAILABLE"
    assert result["rows"][0]["snap_share"] == 0.5
    assert result["rows"][0]["sample"]["snap_count"] == 52
    assert result["rows"][0]["participation_domain"] == "OFFENSE"
    assert result["freshness_state"] == "FRESH"

def test_reader_preserves_stale_snap_share_as_historical_fact():
    rows = [(2026, 1, "gsis-1", "pfr-1", "KC", "DEN", 0.75, "automated:nflverse", "automated", "2026-09-18", "2026-09-19", "snap_counts", "snap_counts_2026", "sha256:test", "snap_share.evidence.v1", "STALE", "COMPLETE", {}, "PUBLISHED")]
    result = read_snap_share(Connection(rows), player_id="gsis-1", season=2026)
    assert result["state"] == "STALE"
    assert result["rows"][0]["snap_share"] == 0.75
    assert result["blockers"] == ["SNAP_SHARE_EVIDENCE_STALE"]
    assert result["authority_state"] == "INFORMATIONAL_ONLY"
    assert result["decision_effect"] == "NONE"


def test_reader_current_fresh_row_not_overridden_by_stale_history():
    rows = [
        (2026, 2, "gsis-1", "pfr-1", "KC", "DEN", 0.80, "automated:nflverse", "automated", "2026-09-20", "2026-09-20", "snap_counts", "snap_counts_2026", "sha256:test", "snap_share.evidence.v1", "FRESH", "COMPLETE", {}, "PUBLISHED"),
        (2026, 1, "gsis-1", "pfr-1", "KC", "DEN", 0.75, "automated:nflverse", "automated", "2026-09-18", "2026-09-19", "snap_counts", "snap_counts_2026", "sha256:test", "snap_share.evidence.v1", "STALE", "COMPLETE", {}, "PUBLISHED"),
    ]
    result = read_snap_share(Connection(rows), player_id="gsis-1", season=2026)
    assert result["state"] == "AVAILABLE"
    assert result["freshness_state"] == "FRESH"
    assert result["rows"][1]["freshness_state"] == "STALE"
    assert result["blockers"] == []


def test_reader_missing_current_snap_value_is_unavailable_not_zero():
    rows = [(2026, 2, "gsis-1", "pfr-1", "KC", "DEN", None, "automated:nflverse", "automated", "2026-09-20", "2026-09-20", "snap_counts", "snap_counts_2026", "sha256:test", "snap_share.evidence.v1", "FRESH", "COMPLETE", {}, "PUBLISHED")]
    result = read_snap_share(Connection(rows), player_id="gsis-1", season=2026)
    assert result["state"] == "UNAVAILABLE"
    assert result["rows"][0]["snap_share"] is None
    assert result["blockers"] == ["SNAP_SHARE_VALUE_UNAVAILABLE"]


def test_reader_missing_identity_is_unavailable_not_zero_or_blocked():
    result = read_snap_share(Connection(), player_id="", season=2026)
    assert result["state"] == "UNAVAILABLE"
    assert result["rows"] == []
    assert result["blockers"] == ["SNAP_SHARE_PLAYER_IDENTITY_UNAVAILABLE"]


def test_waiver_template_discloses_snap_sample_source_freshness_and_unavailable():
    template = (Path(__file__).parents[1] / "templates" / "waivers.html").read_text(encoding="utf-8")
    assert "Snap share: UNAVAILABLE" in template
    assert "snap.source || snapRow.source" in template
    assert "snap.freshness_state" in template
    assert "participation_domain" in template
