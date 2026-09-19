from datetime import datetime, timezone

import pytest

from services.model_only_future_probability import build_model_only_future_probability

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
BASE = {
    "season": 2026,
    "week": 3,
    "game_id": "2026-w3-away-home",
    "home_team": "HOME",
    "away_team": "AWAY",
    "home_elo": 1600,
    "away_elo": 1500,
    "source_identifiers": {"ratings": "nflverse:elo:2026-w3"},
    "source_recorded_at": "2026-09-19T10:00:00+00:00",
    "generated_at": "2026-09-19T10:05:00+00:00",
    "model_version": "test-model-v1",
    "freshness_threshold_id": "test-future-probability-12h",
    "freshness_threshold_seconds": 43200,
    "now": NOW,
}


def build(**updates):
    values = {**BASE, **updates}
    return build_model_only_future_probability(**values)


def test_supported_evidence_reuses_elo_calculation():
    result = build(freshness_threshold_id="future-probability-12h", freshness_threshold_seconds=43200)
    assert result["available"] is True
    assert result["home_win_probability"] == pytest.approx(0.6881562429)
    assert result["away_win_probability"] == pytest.approx(1 - result["home_win_probability"])
    assert result["completeness_state"] == "COMPLETE"


def test_missing_freshness_threshold_keeps_informational_probability_output():
    result = build(freshness_threshold_id=None, freshness_threshold_seconds=None)
    assert result["available"] is False
    assert result["freshness_state"] == "UNAVAILABLE"
    assert result["authority_state"] == "INFORMATIONAL_ONLY"
    assert result["decision_effect"] == "NONE"
    assert result["source_type"] == "MODEL_ONLY"
    assert result["blocker_reasons"] == ["FUTURE_PROBABILITY_FRESHNESS_THRESHOLD_UNAVAILABLE"]
    assert 0 <= result["home_win_probability"] <= 1
    assert 0 <= result["away_win_probability"] <= 1
    assert result["home_win_probability"] + result["away_win_probability"] == pytest.approx(1.0)


def test_missing_elo_is_unavailable():
    result = build(home_elo=None)
    assert result["available"] is False
    assert result["home_win_probability"] is None
    assert "FUTURE_PROBABILITY_ELO_EVIDENCE_UNAVAILABLE" in result["blocker_reasons"]


@pytest.mark.parametrize("field", ["home_elo", "away_elo"])
def test_boolean_elo_is_unavailable(field):
    result = build(**{field: True})
    assert result["home_win_probability"] is None
    assert result["away_win_probability"] is None
    assert "FUTURE_PROBABILITY_ELO_EVIDENCE_UNAVAILABLE" in result["blocker_reasons"]


@pytest.mark.parametrize("value", ["not-a-number", float("inf"), float("nan")])
def test_invalid_elo_is_unavailable(value):
    result = build(home_elo=value)
    assert result["home_win_probability"] is None
    assert result["away_win_probability"] is None
    assert "FUTURE_PROBABILITY_ELO_EVIDENCE_UNAVAILABLE" in result["blocker_reasons"]


def test_missing_identity_is_unavailable():
    result = build(game_id="", home_team="AWAY")
    assert result["available"] is False
    assert "FUTURE_PROBABILITY_GAME_IDENTITY_UNAVAILABLE" in result["blocker_reasons"]


def test_missing_timestamp_is_unavailable():
    result = build(source_recorded_at=None)
    assert result["available"] is False
    assert "FUTURE_PROBABILITY_SOURCE_TIMESTAMP_UNAVAILABLE" in result["blocker_reasons"]


def test_missing_model_version_is_unavailable():
    result = build(model_version="")
    assert result["available"] is False
    assert "FUTURE_PROBABILITY_MODEL_VERSION_UNAVAILABLE" in result["blocker_reasons"]


def test_missing_freshness_threshold_is_unavailable():
    result = build(freshness_threshold_id=None)
    assert result["available"] is False
    assert "FUTURE_PROBABILITY_FRESHNESS_THRESHOLD_UNAVAILABLE" in result["blocker_reasons"]


def test_stale_evidence_is_unavailable_and_not_current():
    result = build(source_recorded_at="2026-09-18T00:00:00+00:00")
    assert result["available"] is False
    assert result["freshness_state"] == "STALE"
    assert result["home_win_probability"] is None


def test_provenance_authority_and_decision_effect_are_explicit():
    result = build()
    assert result["source_type"] == "MODEL_ONLY"
    assert result["authority_state"] == "INFORMATIONAL_ONLY"
    assert result["decision_effect"] == "NONE"
    assert result["lineage"]["calculation"] == "market_intelligence.elo_home"


def test_situational_inputs_are_lineage_only():
    result = build(situational_inputs={"home": 1.2, "away": -0.5})
    assert result["available"] is True
    assert result["lineage"]["situational_inputs_supplied"] is True


def test_invalid_source_identifier_is_unavailable():
    result = build(source_identifiers={"ratings": None})
    assert result["available"] is False
    assert "FUTURE_PROBABILITY_SOURCE_ID_UNAVAILABLE" in result["blocker_reasons"]
