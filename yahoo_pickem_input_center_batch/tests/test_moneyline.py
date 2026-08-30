import unittest
from pickem_inputs_routes import american_implied,no_vig_home_probability,parse_pct
class MoneylineTests(unittest.TestCase):
    def test_favorite(self): self.assertAlmostEqual(american_implied(-150),.6)
    def test_underdog(self): self.assertAlmostEqual(american_implied(150),.4)
    def test_no_vig(self): self.assertTrue(0 < no_vig_home_probability(140,-160) < 1)
    def test_percent(self): self.assertEqual(parse_pct('72','x'),.72)
if __name__=='__main__': unittest.main()
