import pytest

from survivor_intelligence import build_recommendations, stability_score, summarize


def make_row(game_id="g1", week=1, home_team="H", away_team="A", model_probability=0.70):
    return {
        "game_id": game_id,
        "week": week,
        "away_team": away_team,
        "home_team": home_team,
        "model_pick": home_team,
        "model_probability": model_probability,
        "model_home_probability": model_probability,
        "market_home_probability": 0.70,
        "elo_home_probability": 0.65,
        "situation_home_probability": 0.60,
        "signal": "LEAN",
    }


def test_used_teams_are_excluded():
    rows = [make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70)]
    result = build_recommendations(rows, [], ["H"], {}, strategy="balanced")
    assert result == []


def test_used_teams_are_excluded_for_multiple_candidates():
    rows = [
        make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70),
        make_row(game_id="g2", home_team="B", away_team="C", model_probability=0.68),
    ]
    result = build_recommendations(rows, [], ["H"], {}, strategy="balanced")
    assert [row["team"] for row in result] == ["B"]


def test_primary_is_not_repeated_in_fallbacks():
    rows = [
        make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.72),
        make_row(game_id="g2", home_team="M", away_team="N", model_probability=0.71),
        make_row(game_id="g3", home_team="X", away_team="Y", model_probability=0.69),
    ]
    summary = summarize(build_recommendations(rows, [], [], {}, strategy="balanced"))
    assert summary["primary"]["team"] not in {row["team"] for row in summary["fallbacks"]}


def test_fallbacks_are_unique_and_capped_at_two():
    rows = [
        make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.72),
        make_row(game_id="g2", home_team="M", away_team="N", model_probability=0.71),
        make_row(game_id="g3", home_team="X", away_team="Y", model_probability=0.70),
    ]
    summary = summarize(build_recommendations(rows, [], [], {}, strategy="balanced"))
    fallback_teams = [row["team"] for row in summary["fallbacks"]]
    assert len(fallback_teams) == 2
    assert len(set(fallback_teams)) == 2


def test_identical_inputs_remain_deterministic():
    rows = [
        make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70),
        make_row(game_id="g2", home_team="M", away_team="N", model_probability=0.68),
    ]
    first = build_recommendations(rows, [], [], {}, strategy="balanced")
    second = build_recommendations(rows, [], [], {}, strategy="balanced")
    assert first == second
    assert summarize(first) == summarize(second)


def test_equal_scores_keep_a_deterministic_input_order():
    rows = [
        make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70),
        make_row(game_id="g2", home_team="M", away_team="N", model_probability=0.70),
    ]
    first = build_recommendations(rows, [], [], {}, strategy="balanced")
    second = build_recommendations(rows, [], [], {}, strategy="balanced")
    assert first == second
    assert [row["team"] for row in first] == ["H", "M"]


def test_current_probability_is_clamped_to_0_to_1():
    rows = [make_row(game_id="g1", home_team="H", away_team="A", model_probability=1.5)]
    result = build_recommendations(rows, [], [], {}, strategy="balanced")
    assert result[0]["current_probability"] == 1.0


def test_future_value_is_normalized_to_0_to_1():
    rows = [make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70)]
    schedule = [{"week": 2, "away_team": "A", "home_team": "H"}]
    predictions_by_game = {(2, "A", "H"): {"model_home_probability": 0.70, "home_team": "H", "away_team": "A"}}
    result = build_recommendations(rows, schedule, [], predictions_by_game, strategy="balanced")
    assert result[0]["future_available"] is True
    future_value = result[0]["future_value"]
    assert 0.0 <= future_value <= 1.0
    assert result[0]["future_preservation"] == pytest.approx(1.0 - future_value)


def test_missing_future_evidence_is_none_not_fifty_percent():
    rows = [make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70)]
    result = build_recommendations(rows, [], [], {}, strategy="balanced")
    assert result[0]["future_available"] is False
    assert result[0]["future_value"] is None
    assert result[0]["future_preservation"] is None
    assert result[0]["future_missing_reason"] == "SURVIVOR_FUTURE_EVIDENCE_UNAVAILABLE"
    assert "limited future value" not in result[0]["reason"]
    assert "future opportunity cost is unavailable" in result[0]["reason"]


def test_future_preservation_reduces_willingness_for_higher_future_value():
    base_row = make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70)
    rows_low = [base_row]
    rows_high = [base_row]
    schedule = [{"week": 2, "away_team": "A", "home_team": "H"}]
    low_future = {(2, "A", "H"): {"model_home_probability": 0.30, "home_team": "H", "away_team": "A"}}
    high_future = {(2, "A", "H"): {"model_home_probability": 0.90, "home_team": "H", "away_team": "A"}}
    low_score = build_recommendations(rows_low, schedule, [], low_future, strategy="balanced")[0]["survivor_score"]
    high_score = build_recommendations(rows_high, schedule, [], high_future, strategy="balanced")[0]["survivor_score"]
    assert low_score > high_score


def test_empty_candidate_input_is_handled_safely():
    assert build_recommendations([], [], [], {}, strategy="balanced") == []
    summary = summarize([])
    assert summary["primary"] is None
    assert summary["fallbacks"] == []
    assert summary["avoid"] == []
    assert summary["save_for_later"] == []
    assert summary["risks"] == []
    assert summary["multi_week_roadmap"]["state"] == "UNAVAILABLE"


def test_all_used_candidates_are_handled_safely():
    rows = [make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70)]
    assert build_recommendations(rows, [], ["H"], {}, strategy="balanced") == []
    summary = summarize(build_recommendations(rows, [], ["H"], {}, strategy="balanced"))
    assert summary["primary"] is None
    assert summary["fallbacks"] == []
    assert summary["avoid"] == []


def test_missing_current_runtime_field_is_not_fabricated():
    rows = [{
        "game_id": "g1",
        "week": 1,
        "away_team": "A",
        "home_team": "H",
        "model_pick": "H",
        "model_home_probability": 0.70,
        "market_home_probability": 0.70,
        "elo_home_probability": 0.65,
        "situation_home_probability": 0.60,
    }]
    with pytest.raises(KeyError):
        build_recommendations(rows, [], [], {}, strategy="balanced")


@pytest.mark.parametrize(
    "strategy, expected_weights, expected_stability",
    [
        ("protect-lead", (0.90, 0.10), 0.80),
        ("balanced", (0.88, 0.12), 0.80),
        ("gain-ground", (0.85, 0.15), 0.80),
    ],
)
def test_strategy_names_resolve_to_current_implemented_weights(strategy, expected_weights, expected_stability):
    rows = [make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70)]
    result = build_recommendations(rows, [], [], {}, strategy=strategy)[0]
    expected_score = 0.70 * expected_weights[0] + expected_stability * expected_weights[1]
    assert result["survivor_score"] == pytest.approx(expected_score)
    assert result["survivor_score_basis"] == "current_stability_only"
    assert result["future_preservation"] is None
    assert result["stability"] == pytest.approx(expected_stability)


@pytest.mark.xfail(reason="Documented Survivor component is not available in active runtime data")
def test_documented_60_20_10_10_target_is_not_available_in_active_runtime():
    rows = [make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70)]
    result = build_recommendations(rows, [], [], {}, strategy="balanced")[0]
    assert result["survivor_score"] == pytest.approx(0.60 * 0.70 + 0.20 * 0.50 + 0.10 * 0.50 + 0.10 * 0.00)


def test_unknown_strategy_uses_balanced_behavior():
    rows = [make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70)]
    known = build_recommendations(rows, [], [], {}, strategy="balanced")[0]["survivor_score"]
    unknown = build_recommendations(rows, [], [], {}, strategy="mystery")[0]["survivor_score"]
    assert unknown == pytest.approx(known)


def test_stability_score_is_none_when_all_components_missing():
    row = {"market_home_probability": None, "elo_home_probability": None, "situation_home_probability": None}
    assert stability_score(row) is None


def test_stability_score_is_none_when_any_single_component_missing():
    row = {"market_home_probability": 0.7, "elo_home_probability": None, "situation_home_probability": 0.6}
    assert stability_score(row) is None


def test_stability_score_does_not_fabricate_perfect_agreement_when_all_missing():
    """Regression guard: previously `or .5` fallbacks made an all-missing row look like 100% agreement."""
    row = {"market_home_probability": None, "elo_home_probability": None, "situation_home_probability": None}
    assert stability_score(row) != 1.0
    assert stability_score(row) is None


def test_missing_evidence_agreement_renders_unavailable_not_a_number():
    row = make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70)
    row["market_home_probability"] = None
    row["elo_home_probability"] = None
    row["situation_home_probability"] = None
    result = build_recommendations([row], [], [], {}, strategy="balanced")[0]
    assert result["stability_available"] is False
    assert result["stability"] is None
    assert result["survivor_score_basis"] == "current_only"
    assert result["survivor_score"] == pytest.approx(0.70)
    assert "evidence agreement is unavailable" in result["reason"]


def test_missing_evidence_agreement_produces_a_risk_entry():
    row = make_row(game_id="g1", home_team="H", away_team="A", model_probability=0.70)
    row["market_home_probability"] = None
    row["elo_home_probability"] = None
    row["situation_home_probability"] = None
    summary = summarize(build_recommendations([row], [], [], {}, strategy="balanced"))
    assert summary["risks"][0]["evidence_state"] == "UNAVAILABLE"
    assert summary["risks"][0]["affected_recommendation"] == "H"
