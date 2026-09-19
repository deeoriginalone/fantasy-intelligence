from services.unified_decision_context import build_unified_decision_context

NOW = "2026-09-16T12:00:00+00:00"


def complete(**updates):
    values = {
        "season": 2026,
        "week": 3,
        "decision_type": "LINEUP",
        "decision_subject": {"player_id": "player-123", "slot": "WR1"},
        "decision_subject_type": "PLAYER_SLOT",
        "stable_identity": {"player_id": "player-123", "team": "SEA"},
        "decision_output": {"decision": "START"},
        "source": "verified weekly lineup context",
        "source_recorded_at": NOW,
        "retrieved_at": NOW,
        "freshness_state": "FRESH",
        "completeness_state": "COMPLETE",
        "lineage": {"source": "Sleeper API", "record": "league-1:week-3"},
    }
    values.update(updates)
    return build_unified_decision_context(**values)


def test_complete_context_preserves_authoritative_supplied_fields():
    result = complete()
    assert result["state"] == "AVAILABLE"
    assert result["authoritative"] is False
    assert result["season"] == 2026
    assert result["week"] == 3
    assert result["decision_type"] == "LINEUP"
    assert result["decision_subject"]["player_id"] == "player-123"
    assert result["decision_output"] == {"decision": "START"}
    assert result["source_recorded_at"] == NOW
    assert result["retrieved_at"] == NOW
    assert result["decision_effect"] == "NONE"


def test_context_is_consistent_for_lineup_waiver_and_trade_shapes():
    contexts = [
        complete(decision_type="LINEUP", decision_output={"decision": "START"}),
        complete(decision_type="WAIVER", decision_output={"action": "CLAIM"}),
        complete(decision_type="TRADE", decision_output={"action": "REVIEW"}),
    ]
    assert {(item["season"], item["week"]) for item in contexts} == {(2026, 3)}
    assert all(item["state"] == "AVAILABLE" for item in contexts)


def test_missing_required_fields_fail_closed_without_defaults():
    result = build_unified_decision_context(
        decision_type="LINEUP",
        decision_output={"decision": "START"},
        freshness_state="FRESH",
        completeness_state="COMPLETE",
    )
    assert result["state"] == "INSUFFICIENT_EVIDENCE"
    assert result["season"] is None
    assert result["week"] is None
    assert "MISSING_SEASON" in result["blockers"]
    assert "MISSING_WEEK" in result["blockers"]
    assert "MISSING_DECISION_SUBJECT" in result["blockers"]


def test_unsafe_week_and_subject_identity_are_not_invented():
    result = complete(week="1", stable_identity=None, decision_subject_type=None)
    assert result["week"] is None
    assert result["stable_identity"] is None
    assert result["decision_subject_type"] is None
    assert "MISSING_WEEK" in result["blockers"]


def test_stale_and_unsupported_freshness_remain_fail_closed():
    stale = complete(freshness_state="STALE")
    unsupported = complete(freshness_state="MYSTERY")
    assert stale["state"] == "STALE"
    assert "FRESHNESS_STALE" in stale["blockers"]
    assert unsupported["state"] == "BLOCKED"
    assert "FRESHNESS_BLOCKED" in unsupported["blockers"]


def test_context_does_not_mutate_supplied_decision_output():
    output = {"decision": "START"}
    result = complete(decision_output=output)
    output["decision"] = "SIT"
    assert result["decision_output"] == {"decision": "START"}
