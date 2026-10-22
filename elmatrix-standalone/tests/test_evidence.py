import sqlite3, tempfile, unittest
from pathlib import Path
from elmatrix.evidence import parse_rss, canonicalize_url, open_db, save_evidence, list_evidence
from elmatrix.ranking import rank_with_evidence

RSS=b"""<?xml version="1.0"?><rss version="2.0"><channel><item><title>Example trend</title><link>https://example.com/story?utm_source=test</link><description>Users ask about an example task.</description><pubDate>Wed, 21 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>"""
class EvidenceTests(unittest.TestCase):
 def test_canonical_url_drops_tracking(self):
  self.assertEqual(canonicalize_url("https://EXAMPLE.com/a?utm_source=x&id=4#frag"),"https://example.com/a?id=4")
 def test_rejects_non_http(self):
  with self.assertRaises(ValueError): canonicalize_url("file:///etc/passwd")
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
if __name__=="__main__": unittest.main()
