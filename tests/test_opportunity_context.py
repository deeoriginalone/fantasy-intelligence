from services.opportunity_context import opportunity_strength, opportunity_trend, usage_stability


def test_opportunity_strength_exposes_inputs_and_state_without_quality_claims():
    result = opportunity_strength(
        usage_row={"target_share": 0.8, "carry_share": 0.6, "touch_share": 0.7},
        snap_row={"snap_share": 0.9},
    )
    assert result["state"] == "HIGH_OPPORTUNITY"
    assert result["inputs"]["snap_share"] == 0.9
    assert "player quality" in result["reason"]


def test_opportunity_strength_missing_evidence_fails_closed():
    result = opportunity_strength(usage_row={}, snap_row={})
    assert result["state"] == "UNAVAILABLE"


def test_usage_stability_requires_current_and_prior_rows():
    result = usage_stability(
        current_usage={"target_share": 0.4, "carry_share": 0.2, "touch_share": 0.3},
        prior_usage={"target_share": 0.2, "carry_share": 0.1, "touch_share": 0.2},
        current_snap={"snap_share": 0.8},
        prior_snap={"snap_share": 0.6},
    )
    assert result["state"] == "INCREASING"
    assert "target_share" in result["compared_metrics"]


def test_usage_stability_missing_prior_is_insufficient():
    result = usage_stability(current_usage={"target_share": 0.4}, prior_usage={}, current_snap={}, prior_snap={})
    assert result["state"] == "INSUFFICIENT_EVIDENCE"


def test_opportunity_trend_reports_published_drivers_and_state():
    stability = usage_stability(
        current_usage={"target_share": 0.4, "carry_share": 0.2, "touch_share": 0.3},
        prior_usage={"target_share": 0.2, "carry_share": 0.1, "touch_share": 0.2},
        current_snap={"snap_share": 0.8}, prior_snap={"snap_share": 0.6},
    )
    result = opportunity_trend(strength={"inputs": {"snap_share": 0.8}}, stability=stability)
    assert result["state"] == "IMPROVING"
    assert "Snap Share +20.0%" in result["drivers"]
    assert "Target Share +20.0%" in result["drivers"]


def test_opportunity_trend_requires_comparison_evidence():
    result = opportunity_trend(strength={"inputs": {}}, stability={"state": "INSUFFICIENT_EVIDENCE"})
    assert result["state"] == "INSUFFICIENT_EVIDENCE"
    assert result["drivers"] == []


def test_usage_stability_explains_single_week_limit():
    result = usage_stability(
        current_usage={"target_share": 0.4},
        prior_usage={},
        current_snap={"snap_share": 0.8},
        prior_snap={},
    )
    assert result["state"] == "INSUFFICIENT_EVIDENCE"
    assert "One supported week is available" in result["reason"] or "current and prior" in result["reason"]
