from services.opportunity_evidence import METRICS, build_opportunity_evidence, build_what_changed


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
