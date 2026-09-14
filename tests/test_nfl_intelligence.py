from datetime import datetime, timedelta, timezone

from nfl_intelligence import build_game, classify_signal, confidence_label, game_action, injury_impact_label, team_signal_payload


NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def row(market_home=0.8, market_updated_at=None, model_probability=0.8, model_pick="H", projected_total=None):
    return {
        "game_id": "g1", "away_team": "A", "home_team": "H",
        "model_pick": model_pick, "model_probability": model_probability,
        "market_home_probability": market_home, "elo_home_probability": 0.5085,
        "situation_home_probability": 0.5, "market_updated_at": market_updated_at,
        "projected_total": projected_total,
    }


def test_no_wagering_terms_in_signal_vocabulary():
    for value in ("STRONG SIGNAL", "MODERATE SIGNAL", "LOW SIGNAL", "INSUFFICIENT EVIDENCE"):
        for banned in ("BET", "PICK", "LOCK", "WAGER", "ODDS SHOP", "ROI"):
            assert banned not in value


def test_classify_strong_signal_requires_confidence_and_edge():
    assert classify_signal(0.9, True, 0.9, "FRESH") == "STRONG SIGNAL"


def test_classify_insufficient_evidence_when_stale():
    assert classify_signal(0.9, True, 0.9, "STALE") == "INSUFFICIENT EVIDENCE"
    assert classify_signal(0.9, True, 0.9, "UNAVAILABLE") == "INSUFFICIENT EVIDENCE"


def test_classify_low_signal_when_confidence_missing():
    assert classify_signal(0.9, False, None, "FRESH") == "LOW SIGNAL"


def test_confidence_is_separate_from_win_probability():
    r = row(market_home=0.8, market_updated_at=NOW)
    game = build_game(r, now=NOW)
    assert game["win_probability"] != game["confidence"]
    assert "confidence" in game and "win_probability" in game


def test_game_without_prediction_renders_insufficient_evidence_not_hidden():
    r = row(model_probability=None, model_pick=None, market_updated_at=None)
    game = build_game(r, now=NOW)
    assert game["has_prediction"] is False
    assert game["signal"] == "INSUFFICIENT EVIDENCE"
    assert game["reason"] is not None
    assert game["win_probability"] is None


def test_team_strength_supported_when_real_ratings_present():
    r = row(market_updated_at=NOW)
    ratings = {"A": {"team": "A", "elo_rating": 1450.0}, "H": {"team": "H", "elo_rating": 1600.0}}
    game = build_game(r, ratings=ratings, now=NOW)
    assert game["team_strength_supported"] is True
    assert game["elo_diff"] == 150.0


def test_team_strength_unavailable_without_ratings():
    r = row(market_updated_at=NOW)
    game = build_game(r, ratings={}, now=NOW)
    assert game["team_strength_supported"] is False
    assert game["elo_diff"] is None


def test_injury_total_aggregates_both_teams():
    r = row(market_updated_at=NOW)
    injuries = {
        "A": {"team": "A", "quarterback_points": -4.0, "offensive_line_points": 0.0, "defense_points": 0.0},
        "H": {"team": "H", "quarterback_points": 0.0, "offensive_line_points": -0.5, "defense_points": 0.0},
    }
    game = build_game(r, injuries=injuries, now=NOW)
    assert game["injury_supported"] is True
    assert game["injury_total"] == -4.5


def test_weather_flag_high_on_strong_wind():
    r = row(market_updated_at=NOW)
    weather = {"g1": {"wind_speed_10m": 25.0, "precipitation": 0.0}}
    game = build_game(r, weather=weather, now=NOW)
    assert game["weather_supported"] is True
    assert game["weather_flag"] == "HIGH"


def test_existing_injury_and_weather_data_maps_to_manager_labels():
    assert injury_impact_label(-7) == "HIGH"
    assert injury_impact_label(-3) == "MEDIUM"
    assert injury_impact_label(-1) == "LOW"
    assert game_action(True, True, "STRONG SIGNAL", "FRESH", "LOW", "LOW") == "STRONG SIGNAL"
    assert game_action(True, True, "LOW SIGNAL", "FRESH", "HIGH", "LOW") == "HIGH RISK"
    assert game_action(False, False, "INSUFFICIENT EVIDENCE", "UNAVAILABLE", "UNAVAILABLE", None) == "INSUFFICIENT EVIDENCE"


def test_stale_evidence_produces_a_risk_note():
    r = row(market_updated_at=NOW - timedelta(hours=48))
    game = build_game(r, now=NOW)
    assert game["freshness"] == "STALE"
    assert game["risk"] is not None
    assert game["signal"] == "INSUFFICIENT EVIDENCE"


def test_missing_timestamp_is_unavailable_not_fabricated_fresh():
    r = row(market_updated_at=None)
    game = build_game(r, now=NOW)
    assert game["freshness"] == "UNAVAILABLE"


def test_team_signal_payload_is_pure_and_reusable(monkeypatch):
    import nfl_intelligence

    def fake_intelligence(season, week, now=None):
        return {"games": [build_game(row(market_updated_at=NOW), ratings={"A": {"team": "A", "elo_rating": 1500}, "H": {"team": "H", "elo_rating": 1550}}, now=NOW)]}

    monkeypatch.setattr(nfl_intelligence, "build_week_intelligence", fake_intelligence)
    payload = team_signal_payload(2026, 1)
    assert "A" in payload and "H" in payload
    assert payload["H"]["matchup_edge"] == 50.0


def test_confidence_label_high_medium_low_and_insufficient():
    assert confidence_label(True, 0.9, "FRESH") == "HIGH CONFIDENCE"
    assert confidence_label(True, 0.65, "FRESH") == "MEDIUM CONFIDENCE"
    assert confidence_label(True, 0.3, "FRESH") == "LOW CONFIDENCE"
    assert confidence_label(True, 0.9, "STALE") == "INSUFFICIENT EVIDENCE"
    assert confidence_label(False, None, "FRESH") == "INSUFFICIENT EVIDENCE"
    assert confidence_label(True, 0.9, "FRESH", has_prediction=False) == "INSUFFICIENT EVIDENCE"


def test_confidence_label_never_uses_wagering_terms():
    for banned in ("BET", "PICK", "LOCK", "WAGER", "ODDS SHOP", "ROI"):
        for label in ("HIGH CONFIDENCE", "MEDIUM CONFIDENCE", "LOW CONFIDENCE", "INSUFFICIENT EVIDENCE"):
            assert banned not in label


def test_game_dict_includes_confidence_label():
    r = row(market_updated_at=NOW)
    game = build_game(r, now=NOW)
    assert "confidence_label" in game
    assert game["confidence_label"] in ("HIGH CONFIDENCE", "MEDIUM CONFIDENCE", "LOW CONFIDENCE", "INSUFFICIENT EVIDENCE")
