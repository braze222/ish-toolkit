import sqlite3, tempfile, unittest
from pathlib import Path
from elmatrix.evidence import parse_rss, canonicalize_url, validate_public_url, open_db, save_evidence, list_evidence
from elmatrix.ranking import rank_with_evidence
from elmatrix.reviews import review_evidence, list_reviews, withdraw_review

RSS=b"""<?xml version="1.0"?><rss version="2.0"><channel><item><title>Example trend</title><link>https://example.com/story?utm_source=test</link><description>Users ask about an example task.</description><pubDate>Wed, 21 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>"""
class EvidenceTests(unittest.TestCase):
 def test_canonical_url_drops_tracking(self):
  self.assertEqual(canonicalize_url("https://EXAMPLE.com/a?utm_source=x&id=4#frag"),"https://example.com/a?id=4")
 def test_rejects_non_http(self):
  with self.assertRaises(ValueError): canonicalize_url("file:///etc/passwd")
 def test_rejects_local_and_private_feed_targets(self):
  for url in ("http://127.0.0.1/feed", "http://localhost/feed", "http://169.254.169.254/latest/meta-data", "http://[::1]/feed"):
   with self.subTest(url=url), self.assertRaises(ValueError): validate_public_url(url)
 def test_rejects_embedded_credentials_for_collection(self):
  with self.assertRaises(ValueError): validate_public_url("https://user:pass@example.com/feed")
 def test_parse_rss_and_store_deduplicates(self):
  items=parse_rss(RSS,"https://example.com/feed.xml",retrieved_at="2026-10-22T10:00:00+00:00")
  self.assertEqual(len(items),1)
  self.assertEqual(items[0].canonical_url,"https://example.com/story")
  with tempfile.TemporaryDirectory() as td:
   db=open_db(Path(td)/"test.db")
   self.assertEqual(save_evidence(items,db),1)
   self.assertEqual(save_evidence(items,db),0)
   self.assertEqual(len(list_evidence(db)),1)
   db.close()
 def test_rank_does_not_claim_feed_items_validate_niches(self):
  with tempfile.TemporaryDirectory() as td:
   db=open_db(Path(td)/"test.db")
   save_evidence(parse_rss(RSS,"https://example.com/feed.xml"),db)
   result=rank_with_evidence(db=db)
   self.assertEqual(result["evidence_summary"]["observations"],1)
   self.assertTrue(all(r["evidence_coverage"]["status"]=="unverified" for r in result["results"]))
   db.close()
 def test_review_links_evidence_to_known_opportunity(self):
  with tempfile.TemporaryDirectory() as td:
   db=open_db(Path(td)/"test.db"); save_evidence(parse_rss(RSS,"https://example.com/feed.xml"),db)
   review_evidence(1,"content-short-tutorials","supports","demand_signal","The observation describes repeated user questions.",db=db)
   links=list_reviews(opportunity_id="content-short-tutorials",db=db)
   self.assertEqual(len(links),1); self.assertEqual(links[0]["evidence_id"],1)
   result=rank_with_evidence(db=db)
   row=next(x for x in result["results"] if x["id"]=="content-short-tutorials")
   self.assertEqual(row["evidence_coverage"]["supporting"],1)
   self.assertEqual(row["evidence_coverage"]["status"],"reviewed_supporting_observations")
   db.close()
 def test_contradictions_are_visible_and_withdrawal_keeps_observation(self):
  with tempfile.TemporaryDirectory() as td:
   db=open_db(Path(td)/"test.db"); save_evidence(parse_rss(RSS,"https://example.com/feed.xml"),db)
   review_evidence(1,"content-short-tutorials","contradicts","demand_signal","This source is not direct evidence of purchase intent.",db=db)
   row=next(x for x in rank_with_evidence(db=db)["results"] if x["id"]=="content-short-tutorials")\n   self.assertEqual(row["evidence_coverage"]["status"],"counter_evidence_present")\n   self.assertEqual(row["evidence_coverage"]["contradicting"],1)
   review_id=list_reviews(db=db)[0]["review_id"]; withdraw_review(review_id,db=db)
   self.assertEqual(len(list_reviews(db=db)),0); self.assertEqual(len(list_evidence(db=db)),1)
   db.close()
 def test_rejects_unknown_opportunity_and_evidence(self):
  with tempfile.TemporaryDirectory() as td:
   db=open_db(Path(td)/"test.db")
   with self.assertRaises(ValueError): review_evidence(1,"not-real","supports","other","reason",db=db)
   save_evidence(parse_rss(RSS,"https://example.com/feed.xml"),db)
   with self.assertRaises(ValueError): review_evidence(99,"content-short-tutorials","supports","other","reason",db=db)
   db.close()
if __name__=="__main__": unittest.main()
