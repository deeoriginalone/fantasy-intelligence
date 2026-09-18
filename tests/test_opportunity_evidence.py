from services.opportunity_evidence import DECISION_CENTER_PANELS, METRICS, build_decision_center, build_market_value_evidence, build_nflverse_usage_evidence, build_nflverse_usage_what_changed, build_opportunity_evidence, build_what_changed, classify_market_signal, classify_opportunity_trend, classify_trade_opportunity
from services.opportunity_evidence import METRICS, build_market_value_evidence, build_opportunity_evidence, build_what_changed, classify_market_signal, classify_opportunity_trend, classify_trade_opportunity


NOW = "2026-09-15T12:00:00+00:00"


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


def published_row(week, *, season=2026, player_id="p1", target_share=0.2, carry_share=0.1, touch_share=0.15, **updates):
    result = {
        "player_id": player_id, "season": season, "week": week,
        "target_volume": 4, "carry_volume": 2,
        "target_share": target_share, "carry_share": carry_share, "touch_share": touch_share,
        "source": "automated:nflverse", "source_authority": "automated",
        "source_recorded_at": NOW, "retrieved_at": NOW,
        "artifact_id": "stats_player_week_2026", "version": "2026.09.15",
        "checksum": "sha256:test", "freshness_threshold_id": "opportunity.evidence.v1",
        "freshness_state": "FRESH", "completeness_state": "COMPLETE",
        "publication_state": "PUBLISHED",
        "lineage": {"reconciliation": {"reconciled": True}, "source": "automated:nflverse"},
    }
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


def test_nflverse_usage_contract_publishes_only_proven_fields():
    result = build_nflverse_usage_evidence(
        {"targets": 8, "target_share": 0.22, "carries": 3},
        player_id="player-1", season=2026, week=3, source="automated:nflverse",
        source_recorded_at=NOW, retrieved_at=NOW, freshness_state="FRESH",
    )
    assert result["authoritative"] is True
    assert result["target_volume"] == 8
    assert result["target_share"] == 0.22
    assert result["carry_volume"] == 3
    assert result["snap_share"] is None
    assert result["touch_share"] is None
    assert result["route_participation"] is None
    assert result["decision_effect"] == "NONE"


def test_nflverse_usage_comparison_publishes_workload_not_role_conclusions():
    current = build_nflverse_usage_evidence({"targets": 8, "target_share": 0.22, "carries": 3}, player_id="p", season=2026, week=3, source="source", retrieved_at=NOW, freshness_state="FRESH")
    previous = build_nflverse_usage_evidence({"targets": 4, "target_share": 0.12, "carries": 1}, player_id="p", season=2026, week=2, source="source", retrieved_at=NOW, freshness_state="FRESH")
    baseline = build_nflverse_usage_evidence({"targets": 2, "target_share": 0.06, "carries": 0}, player_id="p", season=2026, week=1, source="source", retrieved_at=NOW, freshness_state="FRESH")
    result = build_nflverse_usage_what_changed(current, previous, baseline)
    assert result["state"] == "AVAILABLE"
    assert result["workload_change"] == "UP"
    assert result["role_change"] == "UNAVAILABLE"
    assert result["target_share_change"]["previous_classification"] == "INCREASING"
    assert result["summaries"] == ["Target Volume Increasing", "Target Share Increasing", "Carry Volume Increasing"]
    assert result["decision_effect"] == "NONE"


def test_nflverse_usage_missing_fields_fails_closed():
    result = build_nflverse_usage_evidence({"targets": 8}, player_id="p", season=2026, week=3, source="source", retrieved_at=NOW, freshness_state="FRESH")
    assert result["authoritative"] is False
    assert "OPPORTUNITY_TARGET_SHARE_UNAVAILABLE" in result["blockers"]
    assert "OPPORTUNITY_CARRIES_UNAVAILABLE" in result["blockers"]


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
    assert available["workload_change"] == "UP"
    assert available["role_change"] == "UP"
    assert {item["label"] for item in available["changes"]} == {"Target Share", "Snap Share", "Red-Zone Usage", "Routes Run"}
    assert all(item["direction"] == "UP" for item in available["changes"])
    assert available["recommendation_impact"].startswith("Evidence only")


def test_what_changed_rejects_unverified_periods_and_has_no_conclusion_labels():
    blocked = build_what_changed(evidence(), {**evidence(), "authoritative": False}, evidence())
    assert blocked["state"] == "UNAVAILABLE"
    text = str(blocked).upper()
    assert not any(label in text for label in ("BREAKOUT", "REGRESSION", "BUY LOW", "SELL HIGH"))


def test_published_what_changed_compares_adjacent_weeks_deterministically():
    result = build_what_changed(
        None, None, None,
        published_weeks=[published_row(1), published_row(2, target_share=0.3, carry_share=0.1, touch_share=0.15)],
    )
    assert result["schema_version"] == "what-changed.v2"
    assert result["state"] == "AVAILABLE"
    assert result["current_week"] == 2
    assert result["prior_comparison_week"] == 1
    assert result["comparison_window_type"] == "ADJACENT"
    target = next(item for item in result["changes"] if item["metric"] == "target_share")
    assert target["current_value"] == 0.3
    assert target["prior_value"] == 0.2
    assert target["absolute_delta"] == 0.1
    assert target["direction"] == "INCREASED"
    assert result["decision_effect"] == "INFORMATIONAL_ONLY"


def test_published_what_changed_discloses_non_adjacent_window():
    result = build_what_changed(None, None, None, published_weeks=[published_row(1), published_row(3)])
    assert result["state"] == "AVAILABLE"
    assert result["current_week"] == 3
    assert result["prior_comparison_week"] == 1
    assert result["comparison_window_type"] == "NON_ADJACENT"


def test_published_what_changed_preserves_zero_and_unavailable_values():
    result = build_what_changed(
        None, None, None,
        published_weeks=[published_row(1, target_share=0.0, carry_share=None), published_row(2, target_share=0.0, carry_share=0.2)],
    )
    target = next(item for item in result["changes"] if item["metric"] == "target_share")
    carry = next(item for item in result["changes"] if item["metric"] == "carry_share")
    assert target["direction"] == "UNCHANGED"
    assert target["absolute_delta"] == 0.0
    assert carry["availability_state"] == "UNAVAILABLE"
    assert carry["absolute_delta"] is None


def test_published_what_changed_requires_current_and_prior_weeks():
    missing_current = build_what_changed(None, None, None, requested_week=2, published_weeks=[published_row(1)])
    missing_prior = build_what_changed(None, None, None, published_weeks=[published_row(2)])
    assert missing_current["blockers"] == ["OPPORTUNITY_CURRENT_WEEK_UNAVAILABLE"]
    assert missing_prior["blockers"] == ["OPPORTUNITY_PRIOR_WEEK_UNAVAILABLE"]


def test_published_what_changed_rejects_cross_season_identity():
    result = build_what_changed(None, None, None, published_weeks=[published_row(1), published_row(2, season=2027)])
    assert result["state"] == "UNAVAILABLE"
    assert result["blockers"] == ["OPPORTUNITY_CROSS_SEASON_COMPARISON_UNAUTHORIZED"]


def test_published_what_changed_fails_closed_for_stale_or_unverified_rows():
    stale = build_what_changed(None, None, None, published_weeks=[published_row(1), published_row(2, freshness_state="STALE")])
    threshold = build_what_changed(None, None, None, published_weeks=[published_row(1), published_row(2, freshness_threshold_id=None)])
    assert stale["state"] == threshold["state"] == "BLOCKED"
    assert "OPPORTUNITY_EVIDENCE_NOT_CURRENT" in stale["blockers"]
    assert any(item.startswith("OPPORTUNITY_PUBLISHED_FIELD_UNAVAILABLE:freshness_threshold_id") for item in threshold["blockers"])


def test_published_what_changed_fails_closed_for_incomplete_duplicate_and_provenance_rows():
    incomplete = build_what_changed(None, None, None, published_weeks=[published_row(1), published_row(2, completeness_state="INCOMPLETE")])
    duplicate = build_what_changed(None, None, None, published_weeks=[published_row(1), published_row(1)])
    provenance = build_what_changed(None, None, None, published_weeks=[published_row(1), published_row(2, checksum=None)])
    unreconciled = build_what_changed(None, None, None, published_weeks=[published_row(1), published_row(2, lineage={"reconciliation": {"reconciled": False}})])
    assert incomplete["state"] == duplicate["state"] == provenance["state"] == "BLOCKED"
    assert "OPPORTUNITY_INCOMPLETE" in incomplete["blockers"]
    assert duplicate["blockers"] == ["OPPORTUNITY_DUPLICATE_PLAYER_WEEK"]
    assert any(item.startswith("OPPORTUNITY_PUBLISHED_FIELD_UNAVAILABLE:checksum") for item in provenance["blockers"])
    assert "OPPORTUNITY_RECONCILIATION_UNVERIFIED" in unreconciled["blockers"]


def test_published_what_changed_keeps_role_metrics_unavailable_and_emits_no_labels():
    result = build_what_changed(None, None, None, published_weeks=[published_row(1), published_row(2)])
    unavailable = {item["metric"]: item for item in result["changes"] if item["availability_state"] == "UNAVAILABLE"}
    assert set(unavailable) == {"snap_share", "route_participation", "red_zone_share", "role_classification"}
    text = str(result).upper()
    assert not any(label in text for label in ("BREAKOUT", "REGRESSION", "BUY LOW", "SELL HIGH", "ADD", "DROP", "START", "SIT"))


def test_opportunity_classification_is_evidence_only():
    growing = classify_opportunity_trend(evidence(0.1), evidence(), evidence(-0.05))
    shrinking = classify_opportunity_trend(evidence(-0.1), evidence(), evidence(0.05))
    stable = classify_opportunity_trend(evidence(), evidence(), evidence())
    assert growing["state"] == "GROWING_OPPORTUNITY"
    assert shrinking["state"] == "SHRINKING_OPPORTUNITY"
    assert stable["state"] == "STABLE_OPPORTUNITY"
    assert growing["decision_effect"] == shrinking["decision_effect"] == stable["decision_effect"] == "NONE"
    assert growing["explanations"] == ["↑ Target Share", "↑ Snap Share", "↑ Touch Share", "↑ Routes Run", "↑ Red-Zone Usage"]


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
