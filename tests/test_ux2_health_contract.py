import pytest

from services.team_health import health_freshness_from_report_date, normalize_health, player_health_contract, team_health_contract


def player(status):
    return {"name": "Test Player", "injury_status": status}


def test_unknown_health_is_not_healthy():
    result = player_health_contract(player(None))
    assert result["state"] == "UNAVAILABLE"
    assert result["health_state"] is None


def test_health_freshness_uses_authoritative_report_date():
    result = health_freshness_from_report_date("2026-09-12", now=__import__("datetime").datetime(2026, 9, 12, 12, tzinfo=__import__("datetime").timezone.utc))
    assert result["freshness_state"] == "FRESH"
    assert result["last_verified"].startswith("2026-09-12T00:00:00")
    assert result["age"] == 43200


def test_missing_health_report_date_is_unavailable():
    assert health_freshness_from_report_date(None) == {"freshness_state": "UNAVAILABLE", "last_verified": None, "age": None}


def test_health_freshness_accepts_retrieved_at_timestamp():
    result = health_freshness_from_report_date("2026-09-12T12:00:00+00:00", now=__import__("datetime").datetime(2026, 9, 12, 12, 0, 1, tzinfo=__import__("datetime").timezone.utc))
    assert result["freshness_state"] == "FRESH"
    assert result["age"] == 1


def test_health_metadata_is_preserved_when_supplied():
    result = team_health_contract(
        [player("ACTIVE")],
        last_verified="2026-09-12T12:00:00+00:00",
        age=3600,
    )
    assert result["last_verified"] == "2026-09-12T12:00:00+00:00"
    assert result["age"] == 3600


def test_missing_health_metadata_is_not_invented():
    result = team_health_contract([player("ACTIVE")])
    assert result["last_verified"] is None
    assert result["age"] is None


def test_team_counts_unknown_separately():
    result = team_health_contract([player("ACTIVE"), player(None), player("Q"), player("OUT")])
    assert result["healthy"] == 1
    assert result["unknown"] == 1
    assert result["questionable"] == 1
    assert result["out"] == 1


def test_team_blocked_fails_closed():
    result = team_health_contract([], blocker="HEALTH_REFRESH_FAILED")
    assert result["state"] == "BLOCKED"
    assert result["healthy"] is None
    assert result["blocker"] == "HEALTH_REFRESH_FAILED"


def test_stale_health_remains_degraded():
    result = team_health_contract([player("ACTIVE")], freshness_state="STALE")
    assert result["state"] == "STALE"
    assert "outdated" in result["recommendation_impact"]


@pytest.mark.parametrize("freshness_state", ["UNKNOWN", "INVALID", "UNSUPPORTED"])
def test_unknown_freshness_returns_safe_unknown_contract(freshness_state):
    result = team_health_contract([player("ACTIVE")], freshness_state=freshness_state)
    assert result["state"] == "UNKNOWN"
    assert result["freshness_state"] == freshness_state
    assert result["healthy"] is None
    assert result["blocker"] == "UNSUPPORTED_HEALTH_FRESHNESS_STATE"
    assert "not trusted" in result["recommendation_impact"]
