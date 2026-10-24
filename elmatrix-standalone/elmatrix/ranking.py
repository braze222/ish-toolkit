"""Evidence-aware ranking with freshness and cautious source-independence indicators."""
from collections import defaultdict
from datetime import datetime, timezone
import re
from urllib.parse import urlparse

from .engine import match_opportunities
from .evidence import open_db
from .reviews import list_reviews, ensure_review_schema

STALE_AFTER_DAYS = 90


def _parse_timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _title_fingerprint(title):
    """Conservative exact-title grouping; not a semantic syndication detector."""
    return " ".join(re.findall(r"[a-z0-9]+", (title or "").casefold()))


def _domain(url):
    try:
        host = (urlparse(url).hostname or "").lower().rstrip(".")
        return host[4:] if host.startswith("www.") else host
    except ValueError:
        return ""


def _freshness(row, now):
    stamp = _parse_timestamp(row.get("published_at")) or _parse_timestamp(row.get("retrieved_at"))
    if stamp is None:
        return {"status": "unknown", "age_days": None, "basis": "no_parseable_date"}
    age_days = max(0, (now - stamp).days)
    return {
        "status": "stale" if age_days > STALE_AFTER_DAYS else "current",
        "age_days": age_days,
        "basis": "published_at" if _parse_timestamp(row.get("published_at")) else "retrieved_at",
    }


def evidence_summary(db=None, limit=500):
    owns = db is None
    db = db or open_db()
    try:
        rows = [dict(r) for r in db.execute(
            """SELECT source_name,canonical_url,retrieved_at,published_at,title,observation,
                      metric,value,region,content_hash FROM evidence
               ORDER BY retrieved_at DESC LIMIT ?""",
            (max(1, min(int(limit), 2000)),),
        )]
        ensure_review_schema(db)
        review_rows = list_reviews(db=db)
    finally:
        if owns:
            db.close()

    now = datetime.now(timezone.utc)
    title_groups = defaultdict(list)
    domains = set()
    for row in rows:
        row["source_domain"] = _domain(row.get("canonical_url", ""))
        row["freshness"] = _freshness(row, now)
        fingerprint = _title_fingerprint(row.get("title", ""))
        if fingerprint:
            title_groups[fingerprint].append(row)
        if row["source_domain"]:
            domains.add(row["source_domain"])

    # Exact normalized title matches across domains are flagged as possible
    # syndication/duplication, never automatically counted as independent proof.
    possible_syndication = 0
    for group in title_groups.values():
        group_domains = {item["source_domain"] for item in group if item["source_domain"]}
        if len(group_domains) > 1:
            possible_syndication += len(group)
            for item in group:
                item["independence_note"] = (
                    "title matches another domain; possible syndication or coincidental title match"
                )
        else:
            for item in group:
                item["independence_note"] = (
                    "no cross-domain exact-title match detected; independence is not verified"
                )

    freshness_counts = {"current": 0, "stale": 0, "unknown": 0}
    for row in rows:
        freshness_counts[row["freshness"]["status"]] += 1

    return {
        "observations": len(rows),
        "unique_urls": len({r["canonical_url"] for r in rows}),
        "unique_sources": len({r["source_name"] for r in rows}),
        "unique_source_domains": len(domains),
        "freshness": freshness_counts,
        "possible_syndicated_or_title_duplicate_items": possible_syndication,
        "independence_notice": (
            "Domain diversity and exact-title matching are screening hints only. "
            "They do not prove editorial independence or corroboration."
        ),
        "items": rows,
        "reviews": review_rows,
    }


def rank_with_evidence(*, budget=0, hours=5, skills=(), models=(), region="global", db=None):
    summary = evidence_summary(db)
    rows = match_opportunities(
        budget=budget, hours=hours, skills=skills, models=models, region=region
    )
    for row in rows:
        linked = [r for r in summary["reviews"] if r["opportunity_id"] == row["id"]]
        reviewed = [r for r in linked if r["state"] == "reviewed"]
        supports = [r for r in reviewed if r["decision"] == "supports"]
        contradicts = [r for r in reviewed if r["decision"] == "contradicts"]
        if not reviewed:
            status = "unverified"
        elif supports and contradicts:
            status = "mixed_signal"
        elif supports:
            status = "reviewed_supporting_observations"
        elif contradicts:
            status = "counter_evidence_present"
        else:
            status = "context_only"

        linked_freshness = []
        for review in reviewed:
            linked_freshness.append(_freshness(review, datetime.now(timezone.utc)))
        stale_count = sum(x["status"] == "stale" for x in linked_freshness)
        unknown_count = sum(x["status"] == "unknown" for x in linked_freshness)
        row["evidence_coverage"] = {
            "linked_observations": len(reviewed),
            "supporting": len(supports),
            "contradicting": len(contradicts),
            "status": status,
            "freshness": {
                "stale": stale_count,
                "unknown": unknown_count,
                "current": len(linked_freshness) - stale_count - unknown_count,
            },
            "items": [
                {
                    "evidence_id": r["evidence_id"],
                    "decision": r["decision"],
                    "claim_type": r["claim_type"],
                    "rationale": r["rationale"],
                    "title": r["title"],
                    "source_name": r["source_name"],
                    "source_url": r["canonical_url"],
                    "published_at": r["published_at"],
                    "retrieved_at": r["retrieved_at"],
                    "freshness": _freshness(r, datetime.now(timezone.utc)),
                    "source_domain": _domain(r["canonical_url"]),
                    "independence_note": (
                        "A human review links this source to the opportunity; source independence "
                        "and corroboration still require manual verification."
                    ),
                }
                for r in reviewed
            ],
            "note": (
                "Human-reviewed source links improve traceability; they do not independently "
                "establish demand, revenue, or profitability."
            ),
        }
        row["ranking_notice"] = "Heuristic fit score; not a live-demand, profit, or revenue estimate."

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evidence_summary": {
            "observations": summary["observations"],
            "unique_urls": summary["unique_urls"],
            "unique_sources": summary["unique_sources"],
            "unique_source_domains": summary["unique_source_domains"],
            "freshness": summary["freshness"],
            "possible_syndicated_or_title_duplicate_items": summary[
                "possible_syndicated_or_title_duplicate_items"
            ],
            "independence_notice": summary["independence_notice"],
            "reviewed_links": len(summary["reviews"]),
        },
        "results": rows,
    }
