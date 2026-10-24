import unittest
from elmatrix.engine import OPPORTUNITIES,match_opportunities
class EngineTests(unittest.TestCase):
 def test_catalog_is_broad(self):
  self.assertGreaterEqual(len(OPPORTUNITIES),22);self.assertGreaterEqual(len({x.category for x in OPPORTUNITIES}),6)
 def test_scores_explainable_and_bounded(self):
  for r in match_opportunities(budget=0,hours=5,skills=["writing"],region="ZA"):
   self.assertGreaterEqual(r["score"],0);self.assertLessEqual(r["score"],100);self.assertIn("cost_fit",r["score_factors"]);self.assertIn("evidence_status",r)
 def test_skill_fit_changes_scores(self):
  a={r["id"]:r["score"] for r in match_opportunities(skills=["writing"])}
  b={r["id"]:r["score"] for r in match_opportunities(skills=["coding"])}
  self.assertNotEqual(a,b)
if __name__=="__main__":unittest.main()
