from pathlib import Path

import owner_operations


def comparison(state="AVAILABLE", **updates):
    result = {
        "state": state,
        "decision_effect": "INFORMATIONAL_ONLY",
        "current_week": 3,
        "prior_comparison_week": 2,
        "comparison_window_type": "ADJACENT",
        "changes": [
            {"metric": "target_share", "label": "Target Share", "availability_state": "AVAILABLE", "prior_value": 0.0, "current_value": 0.2, "direction": "INCREASED"},
            {"metric": "carry_share", "label": "Carry Share", "availability_state": "UNAVAILABLE"},
            {"metric": "touch_share", "label": "Touch Share", "availability_state": "AVAILABLE", "prior_value": 0.2, "current_value": 0.2, "direction": "UNCHANGED"},
            {"metric": "snap_share", "availability_state": "UNAVAILABLE"},
            {"metric": "route_participation", "availability_state": "UNAVAILABLE"},
            {"metric": "red_zone_share", "availability_state": "UNAVAILABLE"},
            {"metric": "role_classification", "availability_state": "UNAVAILABLE"},
        ],
        "summaries": ["Target Share increased from the verified Week 2 value to the verified Week 3 value."],
        "blockers": [],
        "reader_lineage": {"query_mode": "PARAMETERIZED_SELECT_ONLY"},
    }
    result.update(updates)
    return result


def test_team_opportunity_changes_forwards_verified_identity_season_and_week(monkeypatch):
    calls = []

    def fake_adapter(connection, *, player_id, season, week):
        calls.append((connection, player_id, season, week))
        return comparison()

    monkeypatch.setattr(owner_operations, "read_player_what_changed", fake_adapter)
    connection = object()
    result = owner_operations.build_team_opportunity_changes(
        connection,
        [{"player": "A", "opportunity_player_id": "gsis-a"}, {"player": "B"}],
        season=2026,
        week=3,
    )
    assert calls == [(connection, "gsis-a", 2026, 3)]
    assert [item["player"] for item in result["players"]] == ["A", "B"]
    assert result["players"][0]["state"] == "AVAILABLE"
    assert result["players"][1]["state"] == "UNAVAILABLE"
    assert result["players"][1]["blockers"] == ["OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE"]
    assert result["decision_effect"] == "INFORMATIONAL_ONLY"


def test_team_opportunity_changes_isolates_one_blocked_player(monkeypatch):
    def fake_adapter(connection, *, player_id, season, week):
        return comparison("BLOCKED", blockers=["OPPORTUNITY_READER_QUERY_FAILED"]) if player_id == "bad" else comparison()

    monkeypatch.setattr(owner_operations, "read_player_what_changed", fake_adapter)
    result = owner_operations.build_team_opportunity_changes(
        object(),
        [{"player": "Good", "opportunity_player_id": "good"}, {"player": "Bad", "opportunity_player_id": "bad"}],
        season=2026,
        week=3,
    )
    assert result["state"] == "BLOCKED"
    assert result["players"][0]["state"] == "AVAILABLE"
    assert result["players"][1]["blockers"] == ["OPPORTUNITY_READER_QUERY_FAILED"]
    assert "OPPORTUNITY_READER_QUERY_FAILED" in result["blockers"]


def test_team_route_and_template_preserve_informational_what_changed_boundary():
    route = Path("owner_operations.py").read_text(encoding="utf-8")
    start = route.index('@bp.route("/team")')
    end = route.index('@bp.route("/lineup")', start)
    segment = route[start:end]
    assert "build_team_opportunity_changes" in segment
    assert "opportunity_changes=opportunity_changes" in segment
    assert "meta.get(\"season\")" in segment and "meta.get(\"week\")" in segment

    template = Path("templates/team.html").read_text(encoding="utf-8")
    assert "What Changed This Week" in template
    assert "NON_ADJACENT" in template
    assert "target_share" in template and "carry_share" in template and "touch_share" in template
    assert "<details>" in template
    assert "INFORMATIONAL_ONLY" in template
    assert not any(label in template for label in ("BREAKOUT", "REGRESSION", "BUY LOW", "SELL HIGH", "MUST ADD", "TRADE FOR"))
