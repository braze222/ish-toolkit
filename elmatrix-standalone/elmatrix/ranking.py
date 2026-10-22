"""Evidence-aware ranking; reviewed links inform coverage but do not prove market success."""
from datetime import datetime, timezone
from .engine import match_opportunities
from .evidence import open_db
from .reviews import list_reviews, ensure_review_schema

def evidence_summary(db=None, limit=500):
    owns = db is None
    db = db or open_db()
    try:
        rows = [dict(r) for r in db.execute("SELECT source_name,canonical_url,retrieved_at,published_at,title,observation,metric,value,region,content_hash FROM evidence ORDER BY retrieved_at DESC LIMIT ?",(max(1,min(int(limit),2000)),))]
        ensure_review_schema(db)
        review_rows = list_reviews(db=db)
    finally:
        if owns: db.close()
    urls = {r["canonical_url"] for r in rows}
    sources = {r["source_name"] for r in rows}
    return {"observations":len(rows),"unique_urls":len(urls),"unique_sources":len(sources),"items":rows,"reviews":review_rows}

def rank_with_evidence(*, budget=0,hours=5,skills=(),models=(),region="global",db=None):
    summary=evidence_summary(db)
    rows=match_opportunities(budget=budget,hours=hours,skills=skills,models=models,region=region)
    for row in rows:
        linked=[r for r in summary["reviews"] if r["opportunity_id"]==row["id"]]
        reviewed=[r for r in linked if r["state"]=="reviewed"]
        supports=[r for r in reviewed if r["decision"]=="supports"]
        contradicts=[r for r in reviewed if r["decision"]=="contradicts"]
        # A few reviews cannot statistically validate demand. This is coverage, not probability.
        if not reviewed:
            status="unverified"
        elif supports and contradicts:
            status="mixed_signal"
        elif supports:
            status="reviewed_supporting_observations"
        elif contradicts:
            status="counter_evidence_present"
        else:
            status="context_only"
        row["evidence_coverage"]={"linked_observations":len(reviewed),"supporting":len(supports),"contradicting":len(contradicts),
            "status":status,"items":[{"evidence_id":r["evidence_id"],"decision":r["decision"],"claim_type":r["claim_type"],
            "rationale":r["rationale"],"title":r["title"],"source_name":r["source_name"],"source_url":r["canonical_url"],
            "published_at":r["published_at"],"retrieved_at":r["retrieved_at"]} for r in reviewed],
            "note":"Human-reviewed source links improve traceability; they do not independently establish demand, revenue, or profitability."}
        row["ranking_notice"]="Heuristic fit score; not a live-demand, profit, or revenue estimate."
    return {"generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "evidence_summary":{"observations":summary["observations"],"unique_urls":summary["unique_urls"],"unique_sources":summary["unique_sources"],
             "reviewed_links":len(summary["reviews"])},
            "results":rows}
