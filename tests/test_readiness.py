from datetime import datetime, timedelta, timezone

from readiness import evaluate_readiness


def _ts(minutes_ago: int):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def test_ready_state():
    result = evaluate_readiness(
        required_inputs={
            "market_probability": 0.64,
            "ownership": 0.22,
            "qb_status": "healthy",
        },
        optional_inputs={
            "injury_status": "healthy",
            "crowd_percentage": 0.61,
        },
        timestamps={
            "market_probability": _ts(10),
            "crowd_percentage": _ts(15),
            "injury_status": _ts(20),
        },
        freshness_thresholds={
            "market_probability": 1800,
            "crowd_percentage": 1800,
            "injury_status": 86400,
        },
    )
    assert result["readiness_status"] == "READY"
    assert result["reasons"] == []


def test_approximate_state_for_missing_optional_input():
    result = evaluate_readiness(
        required_inputs={
            "market_probability": 0.64,
            "ownership": 0.22,
            "qb_status": "healthy",
        },
        optional_inputs={
            "injury_status": None,
        },
        timestamps={
            "market_probability": _ts(10),
        },
        freshness_thresholds={
            "market_probability": 1800,
        },
    )
    assert result["readiness_status"] == "APPROXIMATE"
    assert any("missing optional input: injury_status" in reason for reason in result["reasons"])


def test_incomplete_for_missing_required_input():
    result = evaluate_readiness(
        required_inputs={
            "market_probability": None,
            "ownership": 0.22,
            "qb_status": "healthy",
        },
        timestamps={
            "ownership": _ts(10),
        },
        freshness_thresholds={
            "ownership": 1800,
        },
    )
    assert result["readiness_status"] == "INCOMPLETE"
    assert any("missing required input: market_probability" in reason for reason in result["reasons"])


def test_stale_market_data():
    result = evaluate_readiness(
        required_inputs={
            "market_probability": 0.64,
            "ownership": 0.22,
            "qb_status": "healthy",
        },
        timestamps={
            "market_probability": _ts(40),
        },
        freshness_thresholds={
            "market_probability": 1800,
        },
    )
    assert result["readiness_status"] == "STALE"
    assert any("stale input: market_probability exceeds 1800s" in reason for reason in result["reasons"])


def test_stale_crowd_data():
    result = evaluate_readiness(
        required_inputs={
            "market_probability": 0.64,
            "ownership": 0.22,
            "qb_status": "healthy",
        },
        timestamps={
            "crowd_percentage": _ts(60),
        },
        freshness_thresholds={
            "crowd_percentage": 1800,
        },
    )
    assert result["readiness_status"] == "STALE"
    assert any("stale input: crowd_percentage exceeds 1800s" in reason for reason in result["reasons"])


def test_stale_injury_data():
    result = evaluate_readiness(
        required_inputs={
            "market_probability": 0.64,
            "ownership": 0.22,
            "qb_status": "healthy",
        },
        timestamps={
            "injury_status": _ts(100000),
        },
        freshness_thresholds={
            "injury_status": 86400,
        },
    )
    assert result["readiness_status"] == "STALE"
    assert any("stale input: injury_status exceeds 86400s" in reason for reason in result["reasons"])


def test_missing_qb_status_is_approximate_or_incomplete():
    result = evaluate_readiness(
        required_inputs={
            "market_probability": 0.64,
            "ownership": 0.22,
            "qb_status": None,
        },
        timestamps={
            "market_probability": _ts(10),
        },
        freshness_thresholds={
            "market_probability": 1800,
        },
    )
    assert result["readiness_status"] in {"APPROXIMATE", "INCOMPLETE"}
    assert any("missing required input: qb_status" in reason for reason in result["reasons"])


def test_duplicate_game_blocks_publication():
    result = evaluate_readiness(
        required_inputs={
            "market_probability": 0.64,
            "ownership": 0.22,
            "qb_status": "healthy",
        },
        blockers=["duplicate game"],
    )
    assert result["readiness_status"] == "BLOCKED"
    assert any("duplicate game" in reason for reason in result["reasons"])


def test_missing_market_probability_blocks():
    result = evaluate_readiness(
        required_inputs={
            "market_probability": None,
            "ownership": 0.22,
            "qb_status": "healthy",
        },
    )
    assert result["readiness_status"] == "INCOMPLETE"
    assert any("missing required input: market_probability" in reason for reason in result["reasons"])


def test_blocked_due_to_duplicate_and_missing_market_probability():
    result = evaluate_readiness(
        required_inputs={
            "market_probability": None,
            "ownership": 0.22,
            "qb_status": "healthy",
        },
        blockers=["duplicate game"],
    )
    assert result["readiness_status"] == "BLOCKED"
    assert any("duplicate game" in reason for reason in result["reasons"])
