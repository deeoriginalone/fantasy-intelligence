import unittest
from survivor_intelligence import build_recommendations,summarize
class T(unittest.TestCase):
 def test_used_excluded(self):
  rows=[{'game_id':'g1','week':1,'away_team':'A','home_team':'H','model_pick':'H','model_probability':.7,'model_home_probability':.7,'market_home_probability':.7,'elo_home_probability':.65,'situation_home_probability':.6,'signal':'LEAN'}]
  self.assertEqual(build_recommendations(rows,[],['H'],{},'balanced'),[])
 def test_primary(self):
  rows=[{'game_id':'g1','week':1,'away_team':'A','home_team':'H','model_pick':'H','model_probability':.7,'model_home_probability':.7,'market_home_probability':.7,'elo_home_probability':.65,'situation_home_probability':.6,'signal':'LEAN'}]
  self.assertEqual(summarize(build_recommendations(rows,[],[],{},'balanced'))['primary']['team'],'H')
if __name__=='__main__':unittest.main()
