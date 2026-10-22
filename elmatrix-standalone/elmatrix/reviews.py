"""Human-reviewed links between source observations and opportunity hypotheses."""
from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from .evidence import open_db
from .engine import OPPORTUNITIES

DECISIONS = {"supports", "contradicts", "context_only", "irrelevant"}
CLAIM_TYPES = {"demand_signal", "customer_pain", "competitor_offer", "pricing", "distribution", "other"}
OPPORTUNITY_IDS = {item.id for item in OPPORTUNITIES}

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def ensure_review_schema(db):
    db.execute("""
    CREATE TABLE IF NOT EXISTS evidence_reviews (
      id INTEGER PRIMARY KEY,
      evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE RESTRICT,
      opportunity_id TEXT NOT NULL,
      decision TEXT NOT NULL CHECK(decision IN ('supports','contradicts','context_only','irrelevant')),
      claim_type TEXT NOT NULL CHECK(claim_type IN ('demand_signal','customer_pain','competitor_offer','pricing','distribution','other')),
      rationale TEXT NOT NULL,
      reviewer TEXT NOT NULL DEFAULT 'local-user',
      state TEXT NOT NULL DEFAULT 'reviewed' CHECK(state IN ('pending','reviewed','withdrawn')),
      reviewed_at TEXT NOT NULL,
      UNIQUE(evidence_id, opportunity_id, claim_type)
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS evidence_reviews_opportunity_idx ON evidence_reviews(opportunity_id,state)")
    db.commit()

def review_evidence(evidence_id, opportunity_id, decision, claim_type, rationale, *, db=None, reviewer="local-user"):
    if opportunity_id not in OPPORTUNITY_IDS:
        raise ValueError(f"Unknown opportunity ID: {opportunity_id}")
    if decision not in DECISIONS:
        raise ValueError(f"Invalid decision: {decision}")
    if claim_type not in CLAIM_TYPES:
        raise ValueError(f"Invalid claim type: {claim_type}")
    rationale = " ".join(str(rationale).split())
    if not rationale or len(rationale) > 2000:
        raise ValueError("Rationale must contain 1–2000 characters.")
    reviewer = " ".join(str(reviewer).split())[:120] or "local-user"
    owns = db is None
    db = db or open_db()
    try:
        ensure_review_schema(db)
        exists = db.execute("SELECT 1 FROM evidence WHERE id=?", (int(evidence_id),)).fetchone()
        if not exists:
            raise ValueError(f"Unknown evidence ID: {evidence_id}")
        with db:
            db.execute("""
            INSERT INTO evidence_reviews(evidence_id,opportunity_id,decision,claim_type,rationale,reviewer,state,reviewed_at)
            VALUES(?,?,?,?,?,?, 'reviewed', ?)
            ON CONFLICT(evidence_id,opportunity_id,claim_type) DO UPDATE SET
              decision=excluded.decision,rationale=excluded.rationale,reviewer=excluded.reviewer,
              state='reviewed',reviewed_at=excluded.reviewed_at
            """, (int(evidence_id), opportunity_id, decision, claim_type, rationale, reviewer, utc_now()))
    finally:
        if owns:
            db.close()

def list_reviews(*, opportunity_id=None, db=None, include_withdrawn=False):
    owns = db is None
    db = db or open_db()
    try:
        ensure_review_schema(db)
        clauses=[]; params=[]
        if opportunity_id is not None:
            clauses.append("r.opportunity_id=?"); params.append(opportunity_id)
        if not include_withdrawn:
            clauses.append("r.state='reviewed'")
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        query="""SELECT r.id AS review_id,r.evidence_id,r.opportunity_id,r.decision,r.claim_type,
        r.rationale,r.reviewer,r.state,r.reviewed_at,e.source_name,e.source_url,e.canonical_url,
        e.retrieved_at,e.published_at,e.title,e.observation,e.region,e.content_hash
        FROM evidence_reviews r JOIN evidence e ON e.id=r.evidence_id"""+where+" ORDER BY r.reviewed_at DESC,r.id DESC"
        return [dict(row) for row in db.execute(query,params)]
    finally:
        if owns:
            db.close()

def withdraw_review(review_id, *, db=None):
    owns = db is None
    db = db or open_db()
    try:
        ensure_review_schema(db)
        with db:
            cur = db.execute("UPDATE evidence_reviews SET state='withdrawn',reviewed_at=? WHERE id=?",
                             (utc_now(), int(review_id)))
            if not cur.rowcount:
                raise ValueError(f"Unknown review ID: {review_id}")
    finally:
        if owns:
            db.close()
