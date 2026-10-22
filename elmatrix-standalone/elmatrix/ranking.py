"""Evidence-aware ranking; unknown evidence stays unknown rather than becoming demand."""
from datetime import datetime, timezone
from .engine import match_opportunities
from .evidence import open_db

def evidence_summary(db=None, limit=500):
    owns = db is None
    db = db or open_db()
    try:
        rows = [dict(r) for r in db.execute("SELECT source_name,canonical_url,retrieved_at,published_at,title,observation,metric,value,region FROM evidence ORDER BY retrieved_at DESC LIMIT ?",(max(1,min(int(limit),2000)),))]
    finally:
        if owns: db.close()
    urls = {r["canonical_url"] for r in rows}
    sources = {r["source_name"] for r in rows}
    return {"observations":len(rows),"unique_urls":len(urls),"unique_sources":len(sources),"items":rows}

def rank_with_evidence(*, budget=0,hours=5,skills=(),models=(),region="global",db=None):
    summary=evidence_summary(db)
    rows=match_opportunities(budget=budget,hours=hours,skills=skills,models=models,region=region)
    for row in rows:
        # Evidence is not attributed to a niche automatically: source relevance requires a human review.
        row["evidence_coverage"] = {"linked_observations":0,"status":"unverified","note":"Imported feed items are not automatically treated as evidence for this niche. Review and link relevant observations before changing confidence."}
        row["ranking_notice"]="Heuristic fit score; not a live-demand, profit, or revenue estimate."
    return {"generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "evidence_summary":{"observations":summary["observations"],"unique_urls":summary["unique_urls"],"unique_sources":summary["unique_sources"]},
            "results":rows}
