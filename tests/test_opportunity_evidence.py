from services.opportunity_evidence import METRICS, build_market_value_evidence, build_opportunity_evidence, build_what_changed, classify_market_signal, classify_opportunity_trend


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
