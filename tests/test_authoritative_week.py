from services.authoritative_week import (
    acquire_authoritative_week,
    build_authoritative_week_contract,
    read_application_state_week,
    resolve_week_owners,
)
from weekly_intelligence import current_week

NOW = "2026-09-16T12:00:00+00:00"


def test_application_state_is_authoritative_only_with_matching_persisted_state():
    cursor = Cursor(({"season": 2026, "week": 3}, NOW))
    result = read_application_state_week(cursor, season=2026, retrieved_at=NOW)
    assert result["authoritative"] is True
    assert result["week"] == 3
    assert result["source"] == "application_state"
    assert result["source_authority"] == "application_state.current_week"
    assert result["source_recorded_at"] == NOW
    assert result["retrieved_at"] == NOW
    assert result["lineage"] == {"owner": "application_state.current_week"}
    assert current_week(Cursor(({"season": 2026, "week": 3}, NOW)), sleeper_state_reader=lambda: None) == 3


def test_acquisition_boundary_reads_both_sources_and_resolves_agreement():
    result = acquire_authoritative_week(
        Cursor(({"season": 2026, "week": 3}, NOW)),
        lambda: {"season": 2026, "week": 3},
        season=2026,
        retrieved_at=NOW,
    )
    assert result["authoritative"] is True
    assert result["week"] == 3
    assert len(result["owner_contracts"]) == 2
    assert result["lineage"]["acquisition_boundary"].endswith("acquire_authoritative_week")


def test_acquisition_boundary_fails_closed_on_source_conflict():
    result = acquire_authoritative_week(
        Cursor(({"season": 2026, "week": 3}, NOW)),
        lambda: {"season": 2026, "week": 4},
        season=2026,
        retrieved_at=NOW,
    )
    assert result["authoritative"] is True
    assert result["state"] == "AVAILABLE"
    assert result["week"] == 4
    assert result["authority_agreement"] == "DISAGREEMENT"
    assert "PERSISTED_WEEK_CONFLICT" in result["warnings"]
    assert len(result["conflicting_owners"]) == 2


def test_missing_state_fails_closed_and_never_defaults_to_one():
    result = read_application_state_week(Cursor(None), season=2026, retrieved_at=NOW)
    assert result["state"] == "UNAVAILABLE"
    assert result["week"] is None
    assert "CURRENT_WEEK_STATE_UNAVAILABLE" in result["blockers"]
    assert current_week(Cursor(None), sleeper_state_reader=lambda: None) is None


def test_invalid_or_mismatched_state_fails_closed():
    invalid = read_application_state_week(Cursor(({"season": 2026, "week": 0}, NOW)), season=2026, retrieved_at=NOW)
    mismatch = read_application_state_week(Cursor(({"season": 2025, "week": 3}, NOW)), season=2026, retrieved_at=NOW)
    assert invalid["state"] == "INSUFFICIENT_EVIDENCE"
    assert invalid["week"] is None
    assert "WEEK_UNAVAILABLE" in invalid["blockers"]
    assert mismatch["state"] == "BLOCKED"
    assert mismatch["week"] is None
    assert "CURRENT_WEEK_SEASON_MISMATCH" in mismatch["blockers"]


def test_stale_and_unavailable_contracts_remain_explicit():
    stale = build_authoritative_week_contract(
        season=2026, week=3, source="application_state", source_authority="application_state.current_week",
        retrieved_at=NOW, freshness_state="STALE", completeness_state="COMPLETE",
    )
    unavailable = build_authoritative_week_contract()
    assert stale["state"] == "STALE"
    assert "WEEK_FRESHNESS_STALE" in stale["blockers"]
    assert unavailable["state"] == "UNAVAILABLE"
    assert "WEEK_UNAVAILABLE" in unavailable["blockers"]


def test_conflicting_authoritative_owners_fail_closed():
    first = build_authoritative_week_contract(
        season=2026, week=3, source="application_state", source_authority="application_state.current_week",
        retrieved_at=NOW, freshness_state="FRESH", completeness_state="COMPLETE",
    )
    second = build_authoritative_week_contract(
        season=2026, week=4, source="Sleeper NFL state", source_authority="sleeper.state.nfl",
        retrieved_at=NOW, freshness_state="FRESH", completeness_state="COMPLETE",
    )
    result = resolve_week_owners(first, second)
    assert result["state"] == "AVAILABLE"
    assert result["week"] == 4
    assert result["authority_agreement"] == "DISAGREEMENT"
    assert "PERSISTED_WEEK_CONFLICT" in result["warnings"]


class Cursor:
    def __init__(self, row):
        self.row = row

    def execute(self, query):
        assert "application_state" in query

    def fetchone(self):
        return self.row


def test_read_failure_is_explicit():
    class BrokenCursor:
        def execute(self, query):
            raise RuntimeError("database unavailable")

        def fetchone(self):
            return None

    result = read_application_state_week(BrokenCursor(), season=2026, retrieved_at=NOW)
    assert result["state"] == "BLOCKED"
    assert "CURRENT_WEEK_READ_FAILED" in result["blockers"]
