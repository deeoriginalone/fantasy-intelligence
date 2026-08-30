import unittest
from market_intelligence import implied,no_vig_home,calculate
class T(unittest.TestCase):
 def test_implied(self):self.assertAlmostEqual(implied(-150),.6)
 def test_novig(self):self.assertTrue(0<no_vig_home(140,-160)<1)
 def test_pick(self):
  r=calculate({'game_id':'g','away_team':'A','home_team':'H','market_home_probability':.7,'away_elo':1500,'home_elo':1550,'away_situation_points':0,'home_situation_points':1})
  self.assertEqual(r['model_pick'],'H')
if __name__=='__main__':unittest.main()
