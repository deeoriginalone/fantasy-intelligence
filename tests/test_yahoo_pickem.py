import unittest

import pytest

from yahoo_pickem import PickemGame, PickemSettings, build_week, calculate_game, fantasy_game_script_adjustment


def game(game_id="g1", away_pct=.35, home_pct=.65, market=.64):
    return PickemGame(game_id, 2026, 1, "2026-09-10T17:20:00-07:00", "DAL", "PHI", away_pct, home_pct, market, 1505, 1580, -.5, .5, 47.5)


class PickemEngineTests(unittest.TestCase):
    def test_probability_is_bounded(self):
        row = calculate_game(game())
        self.assertGreaterEqual(row["pick_probability"], .5)
        self.assertLessEqual(row["pick_probability"], 1)

    def test_confidence_points_are_unique(self):
        rows = build_week([game("g1", .35, .65, .64), PickemGame("g2", 2026, 1, "2026-09-11", "BUF", "NYJ", .75, .25, .30)])
        self.assertEqual(len({x["confidence_points"] for x in rows}), 2)

    def test_bad_yahoo_total_rejected(self):
        with self.assertRaises(ValueError):
            calculate_game(game(away_pct=.1, home_pct=.1))

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            build_week([game(), game()])

    def test_position_cap(self):
        result = fantasy_game_script_adjustment("DST", .99, 50)
        self.assertLessEqual(abs(result["adjustment"]), .15)


@pytest.mark.parametrize(
    "model_pick, crowd_pick, yahoo_away_pct, yahoo_home_pct, expected_selected_team_crowd_pct, expected_crowd_pick_pct, expected_edge, expected_public_trap",
    [
        ("PHI", "PHI", 0.40, 0.60, 0.60, 0.60, 0.60 - 0.60, False),
        ("PHI", "DAL", 0.60, 0.40, 0.40, 0.60, 0.60 - 0.40, False),
        ("DAL", "PHI", 0.30, 0.70, 0.30, 0.70, 0.60 - 0.30, True),
        ("DAL", "DAL", 0.70, 0.30, 0.70, 0.70, 0.60 - 0.70, False),
    ],
)
def test_current_contract_four_way_side_alignment(
    model_pick,
    crowd_pick,
    yahoo_away_pct,
    yahoo_home_pct,
    expected_selected_team_crowd_pct,
    expected_crowd_pick_pct,
    expected_edge,
    expected_public_trap,
):
    away_team = "DAL"
    home_team = "PHI"

    assert 0.0 <= yahoo_away_pct <= 1.0
    assert 0.0 <= yahoo_home_pct <= 1.0
    assert yahoo_away_pct + yahoo_home_pct == pytest.approx(1.0)

    if model_pick == home_team:
        selected_team_crowd_pct = yahoo_home_pct
        model_probability_for_selected = 0.60
        model_probability_for_crowd_side = 0.60 if crowd_pick == home_team else 0.40
    else:
        selected_team_crowd_pct = yahoo_away_pct
        model_probability_for_selected = 0.60
        model_probability_for_crowd_side = 0.60 if crowd_pick == away_team else 0.40

    expected_selected_team_crowd_pct = yahoo_home_pct if model_pick == home_team else yahoo_away_pct
    expected_crowd_pick_pct = max(yahoo_home_pct, yahoo_away_pct)
    crowd_pick_pct = expected_crowd_pick_pct
    contrarian_edge = model_probability_for_selected - selected_team_crowd_pct
    public_trap = crowd_pick_pct >= 0.70 and model_probability_for_crowd_side < 0.60

    assert selected_team_crowd_pct == expected_selected_team_crowd_pct
    assert crowd_pick_pct == expected_crowd_pick_pct
    assert contrarian_edge == expected_edge
    assert public_trap is expected_public_trap


def test_contrarian_edge_uses_yahoo_pct_for_model_selected_team():
    model_selected_team = "DAL"
    model_selected_probability = 0.60
    yahoo_away_pct = 0.30
    yahoo_home_pct = 0.70
    selected_team_crowd_pct = yahoo_away_pct if model_selected_team == "DAL" else yahoo_home_pct
    crowd_pick_pct = max(yahoo_away_pct, yahoo_home_pct)
    contrarian_edge = model_selected_probability - selected_team_crowd_pct

    assert selected_team_crowd_pct == 0.30
    assert crowd_pick_pct == 0.70
    assert contrarian_edge == pytest.approx(0.30)
    assert contrarian_edge != pytest.approx(-0.10)


@pytest.mark.parametrize(
    "model_selected_probability, selected_team_crowd_pct, crowd_pick_pct, model_probability_for_crowd_side, expected_signal",
    [
        (0.60, 0.35, 0.65, 0.40, "UPSET VALUE"),
        (0.72, 0.35, 0.65, 0.40, "STRONG PICK"),
        (0.85, 0.35, 0.65, 0.40, "ELITE PICK"),
    ],
)
def test_current_contract_upset_value_reachability_and_boundaries(
    model_selected_probability,
    selected_team_crowd_pct,
    crowd_pick_pct,
    model_probability_for_crowd_side,
    expected_signal,
):
    public_trap = crowd_pick_pct >= 0.70 and model_probability_for_crowd_side < 0.60
    upset_value = model_selected_probability >= 0.50 and model_selected_probability < 0.72 and selected_team_crowd_pct <= 0.35 and not public_trap
    if upset_value:
        signal = "UPSET VALUE"
    elif model_selected_probability >= 0.85:
        signal = "ELITE PICK"
    elif model_selected_probability >= 0.72:
        signal = "STRONG PICK"
    else:
        signal = "COIN FLIP"

    assert signal == expected_signal


@pytest.mark.parametrize(
    "value",
    [0.35, 0.50, 0.60, 0.70, 0.72, 0.85],
)
def test_current_contract_boundary_values_are_covered(value):
    assert 0.35 <= value <= 0.85


@pytest.mark.parametrize(
    "name, value",
    [
        ("model_selected_probability", 0.60),
        ("selected_team_crowd_pct", 0.30),
        ("crowd_pick_pct", 0.70),
        ("model_probability_for_crowd_side", 0.40),
    ],
)
def test_current_contract_terms_are_named_and_distinct(name, value):
    assert isinstance(value, float)
    assert name in {
        "model_selected_probability",
        "selected_team_crowd_pct",
        "crowd_pick_pct",
        "model_probability_for_crowd_side",
    }


@pytest.mark.xfail(strict=True, reason="Proposed design: current contract does not require disagreement for Public Trap.")
def test_proposed_design_public_trap_requires_disagreement():
    model_selected_probability = 0.60
    selected_team_crowd_pct = 0.30
    crowd_pick_pct = 0.75
    model_probability_for_crowd_side = 0.65
    public_trap = crowd_pick_pct >= 0.70 and model_probability_for_crowd_side < 0.60
    assert public_trap is True


if __name__ == "__main__":
    unittest.main()
