from services.opportunity_evidence import DECISION_CENTER_PANELS, METRICS, OPPORTUNITY_TOUCH_SOURCE_FEASIBILITY, build_decision_center, build_market_value_evidence, build_opportunity_evidence, build_opportunity_evidence_contract, build_opportunity_foundation, build_opportunity_trend, build_opportunity_classification, build_opportunity_duration, build_preliminary_opportunity_comparison, build_role_classification, build_what_changed, build_what_changed_contract, classify_market_signal, classify_opportunity_trend, classify_trade_opportunity
from services.opportunity_evidence import METRICS, build_market_value_evidence, build_opportunity_evidence, build_what_changed, classify_market_signal, classify_opportunity_trend, classify_trade_opportunity
from services.player_opportunity_calculation import calculate_player_opportunity


NOW = "2026-09-15T12:00:00+00:00"


def test_phase_1c_touch_source_feasibility_is_explicit_and_fail_closed():
    expected = {
        "offensive_snaps", "snap_share", "routes_run", "route_participation",
        "red_zone_carries", "red_zone_targets", "red_zone_touches",
        "carries_inside_5", "carries_inside_10", "goal_line_touches",
    }
    assert set(OPPORTUNITY_TOUCH_SOURCE_FEASIBILITY) == expected
    assert OPPORTUNITY_TOUCH_SOURCE_FEASIBILITY["offensive_snaps"]["field"] == "offense_snaps"
    assert OPPORTUNITY_TOUCH_SOURCE_FEASIBILITY["snap_share"]["field"] == "offense_pct"
    assert OPPORTUNITY_TOUCH_SOURCE_FEASIBILITY["snap_share"]["status"] == "SEPARATE_FOUNDATION_ONLY"
    for metric in expected - {"offensive_snaps", "snap_share"}:
        record = OPPORTUNITY_TOUCH_SOURCE_FEASIBILITY[metric]
        assert record["status"] == "UNAVAILABLE"
        assert record["source"] is None
        assert record["field"] is None
        assert record["recommendation_effect"] == "NONE"


def foundation_record(**updates):
    record = {
        "player_id": "p1", "player_name": "Example Player", "position": "WR", "available": True,
        "offensive_snaps": 42, "snap_share": 0.8, "rush_attempts": 2, "targets": 7,
        "routes_run": 31, "red_zone_touches": 2, "goal_line_touches": 1, "games_sample": 3,
        "source": "automated:nflverse", "source_record_time": NOW, "retrieved_at": NOW,
        "age": 30, "freshness_state": "FRESH", "completeness_state": "COMPLETE", "evidence_level": "ESTABLISHED",
    }
    record.update(updates)
    return record


def values(offset=0.0):
    return {metric: 0.2 + offset for metric in METRICS}


def evidence(offset=0.0, **updates):
    result = build_opportunity_evidence(
        values(offset),
        source="official usage feed",
        source_recorded_at=NOW,
        retrieved_at=NOW,
        age=60,
        freshness_state="FRESH",
        completeness_state="COMPLETE",
    )
    result.update(updates)
    return result


def test_complete_contract_contains_all_usage_and_evidence_fields():
    result = evidence()
    assert all(result[metric] == 0.2 for metric in METRICS)
    assert result["source"] == "official usage feed"
    assert result["source_recorded_at"] == NOW
    assert result["retrieved_at"] == NOW
    assert result["age"] == 60
    assert result["freshness_state"] == "FRESH"
    assert result["completeness_state"] == "COMPLETE"
    assert result["authoritative"] is True
    assert result["recommendation_impact"].startswith("Informational")


def test_missing_source_or_timestamp_fails_closed():
    missing_source = build_opportunity_evidence(values(), retrieved_at=NOW, freshness_state="FRESH")
    missing_time = build_opportunity_evidence(values(), source="feed", freshness_state="FRESH")
    assert missing_source["freshness_state"] == "UNAVAILABLE"
    assert missing_time["freshness_state"] == "UNAVAILABLE"
    assert not missing_source["authoritative"]
    assert not missing_time["authoritative"]


def test_unknown_invalid_stale_and_unsupported_values_fail_closed():
    unknown = build_opportunity_evidence({**values(), "target_share": None}, source="feed", retrieved_at=NOW, freshness_state="FRESH")
    invalid = build_opportunity_evidence({**values(), "target_share": 2}, source="feed", retrieved_at=NOW, freshness_state="FRESH")
    stale = build_opportunity_evidence(values(), source="feed", retrieved_at=NOW, freshness_state="STALE")
    unsupported = build_opportunity_evidence(values(), source="feed", retrieved_at=NOW, freshness_state="MYSTERY")
    assert unknown["freshness_state"] == invalid["freshness_state"] == "BLOCKED"
    assert stale["freshness_state"] == "STALE"
    assert unsupported["freshness_state"] == "UNAVAILABLE"
    assert not any(item["authoritative"] for item in (unknown, invalid, stale, unsupported))


def test_what_changed_requires_three_verified_periods():
    unavailable = build_what_changed(evidence(), None, evidence())
    available = build_what_changed(evidence(0.1), evidence(), evidence(-0.05))
    assert unavailable["state"] == "UNAVAILABLE"
    assert available["state"] == "AVAILABLE"
    assert {item["label"] for item in available["changes"]} == {"Target Share", "Snap Share", "Red-Zone Usage", "Routes Run"}
    assert all(item["direction"] == "UP" for item in available["changes"])
    assert available["recommendation_impact"].startswith("Evidence only")


def test_what_changed_rejects_unverified_periods_and_has_no_conclusion_labels():
    blocked = build_what_changed(evidence(), {**evidence(), "authoritative": False}, evidence())
    assert blocked["state"] == "UNAVAILABLE"
    text = str(blocked).upper()
    assert not any(label in text for label in ("BREAKOUT", "REGRESSION", "BUY LOW", "SELL HIGH"))


def test_opportunity_classification_is_evidence_only():
    growing = classify_opportunity_trend(evidence(0.1), evidence(), evidence(-0.05))
    shrinking = classify_opportunity_trend(evidence(-0.1), evidence(), evidence(0.05))
    stable = classify_opportunity_trend(evidence(), evidence(), evidence())
    assert growing["state"] == "GROWING_OPPORTUNITY"
    assert shrinking["state"] == "SHRINKING_OPPORTUNITY"
    assert stable["state"] == "STABLE_OPPORTUNITY"
    assert growing["decision_effect"] == shrinking["decision_effect"] == stable["decision_effect"] == "NONE"
    assert growing["explanations"] == ["↑ Target Share", "↑ Snap Share", "↑ Routes Run", "↑ Red-Zone Usage"]


def test_opportunity_classification_fails_closed_for_history_and_evidence():
    insufficient = classify_opportunity_trend(evidence(), None, evidence())
    unavailable = classify_opportunity_trend(None, evidence(), evidence())
    blocked = classify_opportunity_trend(evidence(), {**evidence(), "authoritative": False}, evidence())
    assert insufficient["state"] == "INSUFFICIENT_HISTORY"
    assert unavailable["state"] == "UNAVAILABLE"
    assert blocked["state"] == "UNAVAILABLE"
    assert blocked["blocker"] == "BLOCKED"


def test_market_value_contract_accepts_only_explicit_supported_state():
    result = build_market_value_evidence({
        "market_value_state": "VALUE_RISING",
        "source": "supported market source",
        "source_recorded_at": NOW,
        "retrieved_at": NOW,
        "freshness_state": "FRESH",
        "completeness_state": "COMPLETE",
    })
    assert result["market_value_state"] == "VALUE_RISING"
    assert result["market_value_source"] == "supported market source"
    assert result["authoritative"] is True
    assert result["recommendation_impact"].startswith("Informational")


def test_market_value_contract_fails_closed_for_missing_or_unsupported_evidence():
    missing = build_market_value_evidence({"market_value_state": "VALUE_RISING"})
    incomplete = build_market_value_evidence({
        "market_value_state": "VALUE_RISING", "source": "source", "source_recorded_at": NOW,
        "retrieved_at": NOW, "freshness_state": "FRESH", "completeness_state": "INCOMPLETE",
    })
    unknown = build_market_value_evidence({
        "market_value_state": "MAYBE", "source": "source", "source_recorded_at": NOW,
        "retrieved_at": NOW, "freshness_state": "FRESH", "completeness_state": "COMPLETE",
    })
    assert missing["market_value_state"] == "UNAVAILABLE"
    assert incomplete["market_value_state"] == "INSUFFICIENT_MARKET_DATA"
    assert unknown["market_value_state"] == "UNAVAILABLE"
    assert not any(item["authoritative"] for item in (missing, incomplete, unknown))


def test_market_signal_classification_uses_only_verified_inputs():
    growing = classify_opportunity_trend(evidence(0.1), evidence(), evidence(-0.05))
    shrinking = classify_opportunity_trend(evidence(-0.1), evidence(), evidence(0.05))
    changed = build_what_changed(evidence(0.1), evidence(), evidence(-0.05))
    rising = build_market_value_evidence({"market_value_state": "VALUE_RISING", "source": "source", "source_recorded_at": NOW, "retrieved_at": NOW, "freshness_state": "FRESH", "completeness_state": "COMPLETE"})
    falling = build_market_value_evidence({"market_value_state": "VALUE_FALLING", "source": "source", "source_recorded_at": NOW, "retrieved_at": NOW, "freshness_state": "FRESH", "completeness_state": "COMPLETE"})
    assert classify_market_signal(growing, changed, falling)["market_signal_state"] == "UNDERVALUED_SIGNAL"
    assert classify_market_signal(shrinking, changed, rising)["market_signal_state"] == "OVERVALUED_SIGNAL"
    assert classify_market_signal(growing, changed, rising)["market_signal_state"] == "FAIR_VALUE_SIGNAL"
    assert classify_market_signal(growing, changed, falling)["authoritative"] is True


def test_market_signal_classification_fails_closed():
    market = build_market_value_evidence({"market_value_state": "VALUE_STABLE", "source": "source", "source_recorded_at": NOW, "retrieved_at": NOW, "freshness_state": "FRESH", "completeness_state": "COMPLETE"})
    assert classify_market_signal(None, None, market)["market_signal_state"] == "INSUFFICIENT_MARKET_DATA"
    assert classify_market_signal({}, {"state": "UNAVAILABLE"}, market)["market_signal_state"] == "INSUFFICIENT_MARKET_DATA"
    assert classify_market_signal({"state": "UNKNOWN"}, {"state": "AVAILABLE"}, market)["blocker"] == "BLOCKED"
    assert classify_market_signal({"state": "STABLE_OPPORTUNITY"}, {"state": "AVAILABLE"}, None)["market_signal_state"] == "UNAVAILABLE"


def test_trade_opportunity_is_evidence_only():
    classification = {"state": "GROWING_OPPORTUNITY", "authoritative": True}
    market_value = {"market_value_state": "VALUE_FALLING", "authoritative": True}
    market_signal = {"market_signal_state": "UNDERVALUED_SIGNAL", "authoritative": True}
    candidate = {"candidate_state": "BUY_LOW_CANDIDATE", "authoritative": True}
    present = classify_trade_opportunity(classification, market_value, market_signal, candidate)
    candidate["candidate_state"] = "SELL_HIGH_CANDIDATE"
    weak = classify_trade_opportunity(classification, market_value, market_signal, candidate)
    candidate["candidate_state"] = "FAIR_VALUE"
    none = classify_trade_opportunity(classification, market_value, {"market_signal_state": "FAIR_VALUE_SIGNAL", "authoritative": True}, candidate)
    assert present["trade_opportunity_state"] == "TRADE_OPPORTUNITY_PRESENT"
    assert weak["trade_opportunity_state"] == "TRADE_OPPORTUNITY_WEAK"
    assert none["trade_opportunity_state"] == "TRADE_OPPORTUNITY_NONE"
    assert present["authoritative"] is True


def test_trade_opportunity_fails_closed():
    valid = {"authoritative": True}
    insufficient = classify_trade_opportunity({"state": "INSUFFICIENT_HISTORY", "authoritative": False}, {"market_value_state": "VALUE_FALLING", "authoritative": True}, {"market_signal_state": "UNDERVALUED_SIGNAL", "authoritative": True}, valid)
    blocked = classify_trade_opportunity({"state": "GROWING_OPPORTUNITY", "authoritative": True}, {"market_value_state": "VALUE_FALLING", "authoritative": True}, {"market_signal_state": "UNDERVALUED_SIGNAL", "authoritative": False}, {"candidate_state": "BUY_LOW_CANDIDATE", "authoritative": True})
    unavailable = classify_trade_opportunity(None, None, None, None)
    assert insufficient["trade_opportunity_state"] == "INSUFFICIENT_EVIDENCE"
    assert blocked["blocker"] == "BLOCKED"
    assert unavailable["trade_opportunity_state"] == "UNAVAILABLE"


def test_decision_center_is_summary_only_and_fail_closed():
    center = build_decision_center({"freshness": "UNAVAILABLE", "completeness": "INCOMPLETE", "blocker": "SOURCE_MISSING"})
    assert [item["panel"] for item in center["panels"]] == list(DECISION_CENTER_PANELS)
    assert all(item["status"] in {"BLOCKED", "UNAVAILABLE"} for item in center["panels"])
    assert center["decision_effect"] == "NONE"


def test_opportunity_foundation_complete_evidence_propagates_freshness():
    result = build_opportunity_foundation(foundation_record(), trend={"snap_share_change": 0.1, "touch_change": 1, "target_change": 2, "red_zone_change": 1, "sample_size": 3}, role_evidence={"role": "FLEX_OPTION", "role_confidence": 0.8}, duration_evidence={"duration_classification": "MEDIUM_TERM", "confidence": 0.7}, classification_evidence={"classification": "EXPANDING_USAGE", "role": "FLEX_OPTION", "trend_direction": "UP", "duration": "MEDIUM_TERM", "confidence": 0.8}, what_changed={"category": "TARGETS", "old_value": 4, "new_value": 7})
    assert set(("player_id", "player_name", "position", "available", "offensive_snaps", "snap_share", "rush_attempts", "targets", "routes_run", "red_zone_touches", "goal_line_touches", "games_sample", "source", "source_record_time", "retrieved_at", "age", "freshness_state", "completeness_state", "evidence_level", "blockers", "recommendation_impact")).issubset(result["evidence"])
    assert result["evidence"]["available"] is True
    assert result["trend"]["trend_direction"] == "UP"
    assert result["role"]["role"] == "FLEX_OPTION"
    assert result["duration"]["duration_classification"] == "MEDIUM_TERM"
    assert result["classification"]["classification"] == "EXPANDING_USAGE"
    assert result["what_changed"]["change"] == 3
    assert result["evidence"]["freshness_state"] == result["trend"]["freshness_state"] == result["role"]["freshness_state"] == "FRESH"
    assert result["decision_effect"] == "NONE"


def test_opportunity_foundation_missing_values_fails_closed_without_inference():
    result = build_opportunity_foundation(foundation_record(targets=None, available=True), trend={"sample_size": 1}, role_evidence={}, duration_evidence={}, classification_evidence={})
    assert result["evidence"]["available"] is False
    assert result["evidence"]["targets"] is None
    assert result["trend"]["trend_direction"] == "UNAVAILABLE"
    assert result["role"]["role"] == "UNAVAILABLE"
    assert result["duration"]["duration_classification"] == "UNAVAILABLE"
    assert result["classification"]["classification"] == "UNAVAILABLE"


def test_trend_direction_and_what_changed_fail_closed():
    assert build_opportunity_trend({**foundation_record(), "sample_size": 1, "snap_share_change": 0, "touch_change": 0, "target_change": 0, "red_zone_change": 0})["trend_direction"] == "UNAVAILABLE"
    assert build_opportunity_trend({**foundation_record(), "sample_size": 3, "snap_share_change": 1, "touch_change": -1, "target_change": 0, "red_zone_change": 0})["trend_direction"] == "UNAVAILABLE"
    changed = build_what_changed_contract(foundation_record(), category="TARGETS", old_value=2, new_value=5)
    assert changed["change"] == 3 and changed["direction"] == "UP"
    assert build_what_changed_contract(foundation_record(), category="UNKNOWN", old_value=2, new_value=5)["direction"] == "UNAVAILABLE"


def test_position_appropriate_usage_keeps_unverified_metrics_unavailable():
    result = build_opportunity_evidence_contract({
        "player_id": "rb-1", "position": "RB", "available": True,
        "rush_attempts": 14, "targets": 3, "games_sample": 2,
        "source": "automated:nflverse", "source_record_time": NOW, "retrieved_at": NOW,
        "freshness_state": "FRESH", "completeness_state": "COMPLETE",
    })
    assert result["available"] is True
    assert result["rush_attempts"] == 14
    assert "routes_run" in result["unavailable_metrics"]
    assert result["recommendation_impact"].startswith("Informational")


def test_usage_role_is_not_duration_authority():
    foundation = build_opportunity_foundation({
        "player_id": "wr-1", "position": "WR", "available": True,
        "targets": 7, "games_sample": 2, "snap_share": 0.8,
        "source": "automated:nflverse", "source_record_time": NOW, "retrieved_at": NOW,
        "freshness_state": "FRESH", "completeness_state": "COMPLETE",
    })
    assert foundation["role"]["role"] == "IMMEDIATE_STARTER"
    assert foundation["duration"]["duration_classification"] == "UNAVAILABLE"
    assert foundation["decision_effect"] == "NONE"


def test_preliminary_opportunity_comparison_is_informational_and_within_position():
    foundation = build_opportunity_foundation(foundation_record(), trend={"snap_share_change": 0.1, "touch_change": 1, "target_change": 2, "red_zone_change": 1, "sample_size": 3}, what_changed={"category": "TARGETS", "old_value": 4, "new_value": 7})
    comparison = build_preliminary_opportunity_comparison(foundation, player_id="rb-1", player_name="Usage RB", position="RB")
    assert comparison["status"] == "PRELIMINARY"
    assert comparison["comparison_scope"] == "WITHIN_POSITION_USAGE"
    assert "targets" in comparison["supported_metrics"]
    assert comparison["decision_effect"] == "NONE"
    assert comparison["trend_direction"] == "UP"
    assert "route_participation" in comparison["unavailable_metrics"]


def test_preliminary_opportunity_comparison_fails_closed_without_supported_values():
    foundation = build_opportunity_foundation({"player_id": "rb-2", "position": "RB", "source": "automated:nflverse", "source_record_time": NOW, "retrieved_at": NOW, "freshness_state": "FRESH", "completeness_state": "INCOMPLETE"})
    comparison = build_preliminary_opportunity_comparison(foundation, player_id="rb-2", position="RB")
    assert comparison["status"] == "UNAVAILABLE"
    assert comparison["evidence_level"] == "INSUFFICIENT"
    assert comparison["trend_direction"] == "UNAVAILABLE"
    assert comparison["decision_effect"] == "NONE"


def production_row(player_id, position, **values):
    row = {
        "player_id": player_id, "team": "KC", "opponent_team": "DEN", "position": position,
        "season": 2026, "week": 3, "targets": 1, "carries": 1,
        "passing_yards": 0, "passing_tds": 0, "passing_interceptions": 0,
        "rushing_yards": 0, "rushing_tds": 0, "receptions": 0,
        "receiving_yards": 0, "receiving_tds": 0, "two_point_conversions": 0, "fumbles_lost": 0,
    }
    row.update(values)
    return row


def test_phase_1d_production_fields_are_position_scoped_and_preserve_zero():
    rows = [
        production_row("qb", "QB", passing_yards=250, passing_tds=2, passing_interceptions=1),
        production_row("rb", "RB", rushing_yards=80, rushing_tds=1, receptions=3, receiving_yards=20, receiving_tds=0),
        production_row("wr", "WR", receptions=6, receiving_yards=100, receiving_tds=1),
        production_row("te", "TE", receptions=4, receiving_yards=50, receiving_tds=1),
    ]
    result = calculate_player_opportunity(rows, season=2026, retrieved_at=NOW, now=NOW, threshold_environment={"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400"})
    by_id = {row["player_id"]: row for row in result["rows"]}
    assert by_id["qb"]["passing_yards"] == 250
    assert by_id["qb"]["passing_tds"] == 2
    assert by_id["qb"]["passing_interceptions"] == 1
    assert by_id["rb"]["rushing_yards"] == 80
    assert by_id["rb"]["rushing_tds"] == 1
    assert by_id["rb"]["receptions"] == 3
    assert by_id["rb"]["receiving_yards"] == 20
    assert by_id["rb"]["receiving_tds"] == 0
    assert by_id["wr"]["receptions"] == 6 and by_id["wr"]["receiving_yards"] == 100 and by_id["wr"]["receiving_tds"] == 1
    assert by_id["te"]["receptions"] == 4 and by_id["te"]["receiving_yards"] == 50 and by_id["te"]["receiving_tds"] == 1
    assert all(row["team"] == "KC" and row["opponent_team"] == "DEN" for row in result["rows"])


def test_phase_1d_missing_production_and_freshness_remain_fail_closed():
    missing = production_row("wr", "WR", receiving_tds=None)
    result = calculate_player_opportunity([missing], season=2026, retrieved_at=NOW, now=NOW, threshold_environment={"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400"})
    assert result["rows"] == []
    assert result["production_blockers"][0]["blockers"] == ["PLAYER_WEEK_PRODUCTION_INPUT_UNAVAILABLE:receiving_tds"]
    stale = calculate_player_opportunity([production_row("wr", "WR")], season=2026, retrieved_at="2020-01-01T00:00:00+00:00", now=NOW, threshold_environment={"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400"})
    assert stale["freshness_state"] == "STALE"
    assert all(not row["authoritative"] for row in stale["rows"])


def test_phase_1d_what_changed_includes_production_only_with_compatible_baseline():
    current = {**evidence(0.1), "receptions": 8, "receiving_yards": 110, "receiving_tds": 1, "rushing_yards": 4, "rushing_tds": 0, "passing_yards": 0, "passing_tds": 0}
    previous = {**evidence(), "receptions": 5, "receiving_yards": 70, "receiving_tds": 0, "rushing_yards": 4, "rushing_tds": 0, "passing_yards": 0, "passing_tds": 0}
    baseline = {**evidence(-0.05), "receptions": 4, "receiving_yards": 60, "receiving_tds": 0, "rushing_yards": 3, "rushing_tds": 0, "passing_yards": 0, "passing_tds": 0}
    changed = build_what_changed(current, previous, baseline)
    assert {item["label"] for item in changed["changes"]} >= {"Receptions", "Receiving Yards", "Receiving TDs", "Rushing Yards", "Rushing TDs", "Passing Yards", "Passing TDs"}
    missing_baseline = build_what_changed(current, previous, {**baseline, "receiving_yards": None})
    assert "Receiving Yards" not in {item["label"] for item in missing_baseline["changes"]}


def comparison_reader(*weeks):
    return {"state": "AVAILABLE", "blockers": [], "rows": [
        {"week": week, "targets": targets, "target_share": share, "receptions": rec, "receiving_yards": yards, "receiving_tds": 0,
         "carries": 1, "carry_share": 0.05, "touch_share": 0.1, "rushing_yards": 2, "rushing_tds": 0,
         "freshness_state": "FRESH", "source": "automated:nflverse", "retrieved_at": "2026-09-30T12:00:00+00:00"}
        for week, targets, share, rec, yards in weeks
    ]}


def test_waiver_player_comparison_is_position_aware_and_informational():
    from services.opportunity_evidence import build_waiver_player_comparison
    result = build_waiver_player_comparison(comparison_reader((1, 4, 0.2, 3, 80), (2, 5, 0.22, 4, 90), (3, 9, 0.28, 6, 142)), position="WR")
    assert result["status"] == "PRELIMINARY" and result["decision_effect"] == "NONE"
    assert set(result["usage"]) == {"targets", "target_share"}
    assert set(result["production"]) == {"receptions", "receiving_yards", "receiving_tds"}
    assert result["production"]["receiving_yards"] == 312
    assert "Target Share (Wk 3): 28%" in result["summary"]
    assert "Receiving Yards (Wks 1-3): 312" in result["summary"]
    displays = {item["field"]: item["display"] for item in result["what_changed"]["changes"]}
    assert displays["targets"] == "+4" and displays["receiving_yards"] == "+52"
    assert result["sample"]["weeks"] == 3 and result["rolling_window"]["weeks"] == [1, 2, 3]
    assert not {"rank", "score", "priority", "recommendation"} & set(result)


def test_waiver_player_comparison_fails_closed():
    from services.opportunity_evidence import build_waiver_player_comparison
    assert build_waiver_player_comparison(None, position="RB")["status"] == "UNAVAILABLE"
    assert build_waiver_player_comparison({"state": "BLOCKED", "rows": [], "blockers": ["X"]}, position="RB")["status"] == "BLOCKED"
    assert build_waiver_player_comparison(comparison_reader((1, 4, 0.2, 3, 80)), position="K")["status"] == "NOT_APPLICABLE"
    single = build_waiver_player_comparison(comparison_reader((1, 4, 0.2, 3, 80)), position="RB")
    assert single["what_changed"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert set(single["usage"]) == {"carries", "carry_share", "touch_share"}
    qb = build_waiver_player_comparison(comparison_reader((1, 4, 0.2, 3, 80)), position="QB")
    assert qb["usage"]["pass_attempts"] is None
    assert "Pass Attempts (Wk 1): UNAVAILABLE" in qb["summary"]
    assert "PLAYER_COMPARISON_FIELD_UNAVAILABLE:pass_attempts" in qb["blockers"]
    assert single["limitations"] == ["routes", "red_zone usage", "goal_line usage", "duration"]
