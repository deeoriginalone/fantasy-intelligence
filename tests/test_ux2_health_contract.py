import pytest

from services.team_health import normalize_health, player_health_contract, team_health_contract


def player(status):
    return {"name": "Test Player", "injury_status": status}


def test_unknown_health_is_not_healthy():
    result = player_health_contract(player(None))
    assert result["state"] == "UNAVAILABLE"
    assert result["health_state"] is None


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


@pytest.mark.parametrize("freshness_state", ["UNKNOWN", "INVALID", "UNSUPPORTED"])
def test_unknown_freshness_returns_safe_unknown_contract(freshness_state):
    result = team_health_contract([player("ACTIVE")], freshness_state=freshness_state)
    assert result["state"] == "UNKNOWN"
    assert result["freshness_state"] == freshness_state
    assert result["healthy"] is None
    assert result["blocker"] == "UNSUPPORTED_HEALTH_FRESHNESS_STATE"
    assert "not trusted" in result["recommendation_impact"]
