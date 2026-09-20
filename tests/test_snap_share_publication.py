import pytest

from services.snap_share_publication import publish_snap_share
from services.snap_share_reader import read_snap_share


class Cursor:
    description = []
    def __init__(self, rows=None): self.rows = rows or []; self.statements = []
    def execute(self, sql, params=None): self.statements.append((sql, params))
    def fetchall(self): return self.rows
    def close(self): pass


class Connection:
    def __init__(self, rows=None): self.cursor_obj = Cursor(rows); self.committed = False; self.rolled_back = False
    def cursor(self): return self.cursor_obj
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True


def evidence():
    return {
        "season": 2026,
        "freshness_state": "FRESH",
        "rows": [{"season": 2026, "week": 1, "gsis_id": "gsis-1", "pfr_player_id": "pfr-1", "team": "KC", "opponent": "DEN", "snap_share": 0.75, "authoritative": True}],
        "reconciliation": {"reconciled": True, "duplicate_count": 0, "contradictory_count": 0, "unresolved_identity_count": 0, "ambiguous_identity_count": 0, "contradictory_identity_count": 0},
        "provenance": {"source": "automated:nflverse", "source_authority": "automated", "retrieved_at": "2026-09-20T12:00:00+00:00", "source_recorded_at": "2026-09-19T12:00:00+00:00", "artifact_identifier": "snap_counts", "version": "snap_counts_2026", "checksum": "sha256:test", "freshness_threshold_id": "snap_share.evidence.v1"},
    }


def test_publication_writes_dedicated_snap_share_table_atomically():
    conn = Connection()
    assert publish_snap_share(conn, evidence()) == 1
    assert conn.committed
    sql = conn.cursor_obj.statements[1][0]
    assert "snap_share_evidence" in sql
    assert "PUBLISHED" in conn.cursor_obj.statements[1][1]


def test_publication_fails_closed_for_missing_threshold_state():
    blocked = dict(evidence(), freshness_state="UNAVAILABLE")
    with pytest.raises(ValueError, match="SNAP_SHARE_FRESHNESS_UNAVAILABLE"):
        publish_snap_share(Connection(), blocked)


def test_reader_returns_published_snap_share_newest_first():
    rows = [(2026, 2, "gsis-1", "pfr-1", "KC", "DEN", 0.5, "automated:nflverse", "automated", "2026-09-19", "2026-09-20", "snap_counts", "snap_counts_2026", "sha256:test", "snap_share.evidence.v1", "FRESH", "COMPLETE", {}, "PUBLISHED")]
    result = read_snap_share(Connection(rows), player_id="gsis-1", season=2026)
    assert result["state"] == "AVAILABLE"
    assert result["rows"][0]["snap_share"] == 0.5
    assert result["freshness_state"] == "FRESH"

def test_reader_preserves_stale_snap_share_as_historical_fact():
    rows = [(2026, 1, "gsis-1", "pfr-1", "KC", "DEN", 0.75, "automated:nflverse", "automated", "2026-09-18", "2026-09-19", "snap_counts", "snap_counts_2026", "sha256:test", "snap_share.evidence.v1", "STALE", "COMPLETE", {}, "PUBLISHED")]
    result = read_snap_share(Connection(rows), player_id="gsis-1", season=2026)
    assert result["state"] == "STALE"
    assert result["rows"][0]["snap_share"] == 0.75
    assert result["blockers"] == ["SNAP_SHARE_EVIDENCE_STALE"]
    assert result["authority_state"] == "INFORMATIONAL_ONLY"
    assert result["decision_effect"] == "NONE"


def test_reader_missing_identity_is_unavailable_not_zero_or_blocked():
    result = read_snap_share(Connection(), player_id="", season=2026)
    assert result["state"] == "UNAVAILABLE"
    assert result["rows"] == []
    assert result["blockers"] == ["SNAP_SHARE_PLAYER_IDENTITY_UNAVAILABLE"]
