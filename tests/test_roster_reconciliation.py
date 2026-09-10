from datetime import datetime, timezone

from services.roster_reconciliation import reconcile_roster

TS = datetime(2026, 9, 10, tzinfo=timezone.utc)
PLAYERS = {
    "1": {"full_name": "Josh Allen"},
    "2": {"full_name": "Bijan Robinson"},
    "3": {"full_name": "Amon-Ra St. Brown"},
}


def local(*names):
    return [(index + 1, name, "RB", "") for index, name in enumerate(names)]


def test_matching_rosters_are_allowed():
    result = reconcile_roster(local("Josh Allen", "Bijan Robinson"), {"players": ["1", "2"]}, PLAYERS, TS)
    assert result["status"] == "MATCHED"
    assert result["allowed"] is True
    assert result["roster_updated_at"] == TS


def test_local_only_player_is_divergent():
    result = reconcile_roster(local("Josh Allen", "Amon-Ra St. Brown"), {"players": ["1"]}, PLAYERS, TS)
    assert result["status"] == "DIVERGENT"
    assert result["local_only"] == ["Amon-Ra St. Brown"]


def test_sleeper_only_player_is_divergent():
    result = reconcile_roster(local("Josh Allen"), {"players": ["1", "2"]}, PLAYERS, TS)
    assert result["status"] == "DIVERGENT"
    assert result["sleeper_only"] == ["Bijan Robinson"]


def test_unmapped_sleeper_id_fails_closed():
    result = reconcile_roster(local("Josh Allen"), {"players": ["1", "999"]}, PLAYERS, TS)
    assert result["status"] == "UNKNOWN"
    assert result["allowed"] is False
    assert result["unmapped_player_ids"] == ["999"]


def test_missing_authoritative_roster_fails_closed():
    result = reconcile_roster(local("Josh Allen"), None, PLAYERS, TS)
    assert result["status"] == "UNKNOWN"
    assert "AUTHORITATIVE_SLEEPER_ROSTER_MISSING" in result["blockers"]


def test_missing_snapshot_timestamp_fails_closed():
    result = reconcile_roster(local("Josh Allen"), {"players": ["1"]}, PLAYERS, None)
    assert result["status"] == "UNKNOWN"
    assert result["roster_updated_at"] is None


def test_duplicate_local_player_fails_closed():
    result = reconcile_roster(local("Josh Allen", "Josh Allen"), {"players": ["1"]}, PLAYERS, TS)
    assert result["status"] == "UNKNOWN"
    assert result["duplicate_local_keys"] == ["joshallen"]


def test_invalid_local_row_fails_closed():
    result = reconcile_roster([(1, "", "QB", "")], {"players": []}, PLAYERS, TS)
    assert result["status"] == "UNKNOWN"
    assert result["invalid_local_row_indexes"] == [0]


def test_common_suffixes_and_punctuation_normalize():
    result = reconcile_roster(local("Marvin Harrison Jr."), {"players": ["9"]}, {"9": {"full_name": "Marvin Harrison"}}, TS)
    assert result["status"] == "MATCHED"
