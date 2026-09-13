from services.team_priority import build_team_priority_action


def starter(**changes):
    row = {
        "player": "Player",
        "slot": "WR1",
        "vacant": False,
        "decision": "START",
        "confidence": {"label": "HIGH", "score": 90},
        "reason": "Supported matchup evidence.",
        "evidence_gaps": [],
        "health_evidence": {
            "state": "AVAILABLE",
            "health_state": "HEALTHY",
            "source": "Sleeper",
            "freshness_state": "FRESH",
            "recommendation_impact": "Health evidence supports lineup review.",
        },
    }
    row.update(changes)
    return row


def needs(**overrides):
    result = {position: {"state": "AVAILABLE", "strategic_need": "NO_ACTION", "drivers": []} for position in ("QB", "RB", "WR", "TE", "FLEX", "K", "DEF")}
    result.update(overrides)
    return result


def accuracy(blockers=None):
    return {"blockers": blockers or [], "recommendation_impact": "Review supplied evidence."}


def test_vacancy_has_highest_supported_priority():
    result = build_team_priority_action([starter(player="Vacant", slot="TE", vacant=True, decision="BLOCKED")], needs(), {"state": "AVAILABLE"}, accuracy())
    assert result["action"] == "Fill vacant TE starter slot"
    assert result["metadata"]["affected_slot"] == "TE"


def test_health_monitoring_priority_targets_player():
    result = build_team_priority_action([starter(decision="MONITOR", confidence={"label": "LOW", "score": 35}, evidence_gaps=["PLAYER_HEALTH_UNAVAILABLE"])], needs(), {"state": "UNAVAILABLE", "blocker": "TEAM_HEALTH_UNAVAILABLE"}, accuracy())
    assert result["action"] == "Monitor Player before lineup lock"
    assert result["metadata"]["affected_player"] == "Player"
    assert result["blockers"] == ["PLAYER_HEALTH_UNAVAILABLE"]


def test_depth_action_preserves_driver():
    result = build_team_priority_action([starter()], needs(RB={"state": "AVAILABLE", "strategic_need": "ADD_DEPTH", "drivers": ["3 RB options are available against a depth target of 4."]}), {"state": "AVAILABLE"}, accuracy())
    assert result["action"] == "Add RB depth"
    assert "depth target of 4" in result["reason"]


def test_blocked_review_action_is_fail_closed():
    result = build_team_priority_action([starter(decision="BLOCKED", confidence={"label": "BLOCKED", "score": 0}, health_evidence={"state": "BLOCKED", "blocker": "HEALTH_REFRESH_FAILED", "recommendation_impact": "Health-dependent recommendations are blocked."}, evidence_gaps=["HEALTH_REFRESH_FAILED"])], needs(), {"state": "BLOCKED", "blocker": "HEALTH_REFRESH_FAILED"}, accuracy(["MATCHUP_DATA_MISSING"]))
    assert result["action"] == "Review Player's health evidence before lineup lock"
    assert "HEALTH_REFRESH_FAILED" in result["blockers"]
    assert result["confidence_score"] == 0


def test_priority_selection_is_deterministic():
    rows = [starter(player="A"), starter(player="B", slot="WR2")]
    first = build_team_priority_action(rows, needs(), {"state": "AVAILABLE"}, accuracy())
    second = build_team_priority_action(rows, needs(), {"state": "AVAILABLE"}, accuracy())
    assert first == second
