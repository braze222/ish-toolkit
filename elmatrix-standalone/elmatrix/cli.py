"""Command-line entry point for standalone Elmatrix."""
import argparse, csv, json, os
from pathlib import Path
from .engine import OPPORTUNITIES, match_opportunities
from .evidence import open_db, collect_feed, save_evidence, list_evidence
from .ranking import rank_with_evidence
from .reviews import review_evidence, list_reviews, withdraw_review
from . import __version__

def main(argv=None):
    p=argparse.ArgumentParser(prog="elmatrix", description="Standalone niche matching and validation")
    p.add_argument("--version", action="version", version=f"Elmatrix {__version__}")
    sub=p.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="initialize local research database")
    sub.add_parser("niches", help="list starter opportunity hypotheses")
    m=sub.add_parser("match", help="rank hypotheses for your constraints")
    m.add_argument("--budget",type=int,default=0); m.add_argument("--hours",type=int,default=5)
    m.add_argument("--skills",default=""); m.add_argument("--models",default=""); m.add_argument("--region",default="global")
    r=sub.add_parser("report",help="emit evidence-aware JSON report"); r.add_argument("--format",choices=["json"],default="json")
    e=sub.add_parser("experiment",help="record a validation experiment")
    e.add_argument("--opportunity",required=True); e.add_argument("--hypothesis",required=True); e.add_argument("--metric",required=True); e.add_argument("--target",required=True)
    ex=sub.add_parser("export",help="export starter catalog"); ex.add_argument("--format",choices=["json","csv"],default="csv"); ex.add_argument("--output",required=True)
    research=sub.add_parser("research",help="collect a public RSS/Atom feed (network access is explicit)")
    research.add_argument("--feed",required=True); research.add_argument("--name",default=""); research.add_argument("--query",default=""); research.add_argument("--region",default="global"); research.add_argument("--timeout",type=int,default=8); research.add_argument("--limit",type=int,default=50)
    ev=sub.add_parser("evidence",help="list collected source-linked observations"); ev.add_argument("--limit",type=int,default=50)
    rev=sub.add_parser("review",help="human-review a source observation for an opportunity")
    rev.add_argument("evidence_id",type=int); rev.add_argument("--opportunity",required=True)
    rev.add_argument("--decision",required=True,choices=["supports","contradicts","context_only","irrelevant"])
    rev.add_argument("--claim-type",required=True,choices=["demand_signal","customer_pain","competitor_offer","pricing","distribution","other"])
    rev.add_argument("--rationale",required=True); rev.add_argument("--reviewer",default="local-user")
    links=sub.add_parser("links",help="list reviewed source links"); links.add_argument("--opportunity",default="")
    withdraw=sub.add_parser("withdraw-review",help="withdraw a review without deleting its source observation"); withdraw.add_argument("review_id",type=int)
    args=p.parse_args(argv)
    if args.command=="init":
        db=open_db(); db.close(); print(f"Initialized local store: {Path(os.environ.get('ELMATRIX_HOME',Path.home()/'.elmatrix-standalone'))}"); return 0
    if args.command=="experiment":
        with open_db() as db:
            db.execute("INSERT INTO experiments(opportunity_id,hypothesis,metric,target) VALUES(?,?,?,?)",(args.opportunity,args.hypothesis,args.metric,args.target))
        print("Experiment recorded. Add observations before treating the hypothesis as validated."); return 0
    if args.command=="research":
        try:
            items=collect_feed(args.feed,source_name=args.name or None,query=args.query,region=args.region,timeout=args.timeout,limit=args.limit)
            count=save_evidence(items)
        except (ValueError,RuntimeError) as exc:
            p.exit(2,f"Research failed; no successful report was generated: {exc}\n")
        print(json.dumps({"feed":args.feed,"parsed":len(items),"new_saved":count,"note":"Published items are source-linked observations, not proof of demand or profitability."},indent=2)); return 0
    if args.command=="evidence":
        print(json.dumps(list_evidence(limit=args.limit),indent=2,ensure_ascii=False)); return 0
    if args.command=="review":
        try: review_evidence(args.evidence_id,args.opportunity,args.decision,args.claim_type,args.rationale,reviewer=args.reviewer)
        except (ValueError, RuntimeError) as exc: p.exit(2,f"Review failed: {exc}\n")
        print("Review saved. This records a human assessment, not proof that the claim is true."); return 0
    if args.command=="links":
        print(json.dumps(list_reviews(opportunity_id=args.opportunity or None),indent=2,ensure_ascii=False)); return 0
    if args.command=="withdraw-review":
        try: withdraw_review(args.review_id)
        except ValueError as exc: p.exit(2,f"Could not withdraw review: {exc}\n")
        print("Review withdrawn; original source observation retained."); return 0
    if args.command=="niches": rows=[x.to_dict() for x in OPPORTUNITIES]
    elif args.command=="match":
        rows=match_opportunities(budget=args.budget,hours=args.hours,skills=args.skills.split(","),models=args.models.split(","),region=args.region)
    elif args.command=="report":
        print(json.dumps(rank_with_evidence(),indent=2,ensure_ascii=False)); return 0
    elif args.command=="export":
        rows=[x.to_dict() for x in OPPORTUNITIES]
        dest=Path(args.output)
        if args.format=="json": dest.write_text(json.dumps(rows,indent=2),encoding="utf-8")
        else:
            with dest.open("w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader()
                for row in rows: w.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
        print(f"Exported {len(rows)} hypotheses to {dest}"); return 0
    else: rows=match_opportunities()
    print(json.dumps(rows,indent=2,ensure_ascii=False))
    return 0
if __name__=="__main__": raise SystemExit(main())
