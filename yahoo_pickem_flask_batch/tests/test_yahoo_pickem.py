import unittest
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


if __name__ == "__main__":
    unittest.main()
