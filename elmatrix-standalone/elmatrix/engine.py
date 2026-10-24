"""Transparent heuristic matching for niche hypotheses; not a profitability oracle."""
from dataclasses import asdict, dataclass
from typing import Iterable

@dataclass(frozen=True)
class Opportunity:
    id: str; title: str; category: str; customer: str; offer: str
    models: tuple[str,...]; skills: tuple[str,...]; regions: tuple[str,...]
    startup_cost: int; hours_per_week: int
    demand: int; monetization: int; pain: int; feasibility: int; competition: int; confidence: int
    validation: str
    def to_dict(self):
        row=asdict(self)
        for k in ("models","skills","regions"): row[k]=list(row[k])
        return row

_SEEDS=[
("content-short-tutorials","Short practical tutorials","content","Learners and busy professionals","Publish concise explainers",("ads","affiliate","digital-products"),("writing","video","research"),("global","ZA"),0,5,3,3,3,4,4,2,"Test ten original tutorials and measure retention."),
("content-local-guides","Local service and city guides","content","People searching for local answers","Create accurate local guides",("ads","affiliate","leads"),("writing","research","seo"),("ZA","local"),0,4,3,4,4,4,3,2,"Interview users and validate search intent."),
("content-kids-learning","Original children's learning activities","content","Parents and educators","Create original learning resources",("digital-products","ads"),("writing","design","education"),("global","ZA"),0,5,3,3,4,3,4,2,"Ask educators to review an original sample; follow child-safety rules."),
("content-research-explainers","Evidence-led research explainers","content","Curious learners and professionals","Publish cited explainers",("ads","sponsorship","digital-products"),("writing","research","analysis"),("global","ZA"),0,5,3,3,4,4,4,2,"Publish a cited pilot and ask target readers for feedback."),
("service-cleaning-leads","Cleaning service lead generation","services","Local cleaning operators","Generate qualified enquiries",("leads","retainer"),("sales","research","seo"),("ZA","local"),0,5,4,4,4,4,3,2,"Speak to five providers about qualified leads."),
("service-admin-automation","Small-business admin automation","services","Solo operators and small teams","Set up forms and simple workflows",("service","retainer"),("automation","research","writing"),("global","ZA"),0,5,4,4,4,4,3,2,"Deliver one manual pilot before automating."),
("service-cv-profile","CV and job-profile improvement","services","Job seekers","Edit application materials",("service","digital-products"),("writing","design","research"),("global","ZA"),0,4,4,3,4,5,4,2,"Test a fixed-scope sample with consent."),
("service-tutoring","Focused tutoring support","services","Learners and families","Provide narrow-subject tutoring",("service","subscription"),("education","writing","video"),("global","ZA"),0,4,4,4,4,4,3,2,"Validate the learner segment and outcome."),
("service-local-seo","Local business listing cleanup","services","Local businesses","Improve accurate public listings",("service","retainer"),("seo","research","writing"),("global","ZA"),0,4,4,4,4,4,3,2,"Audit three public listings and interview owners."),
("service-content-repurposing","Content repurposing","services","Experts with long-form content","Turn approved material into drafts",("service","retainer"),("writing","research","video"),("global","ZA"),0,5,4,4,4,4,3,2,"Pilot using owner-provided material and approval."),
("software-niche-directory","Niche searchable directory","software","A professional or local community","Curate a trusted directory",("subscription","leads","sponsorship"),("research","coding","seo"),("global","ZA"),0,6,3,4,3,3,4,2,"Curate 30 entries and test repeat usage."),
("software-micro-saas","Small workflow utility","software","One narrow professional segment","Solve a recurring task",("subscription","license"),("coding","research","design"),("global","ZA"),0,8,4,4,5,2,4,2,"Interview ten users before prototyping."),
("software-open-source-support","Open-source setup support","software","Users of a specific tool","Offer setup and documentation support",("service","sponsorship"),("coding","writing","research"),("global","ZA"),0,5,3,3,3,4,3,2,"Identify recurring setup issues."),
("software-template-generator","Template or document generator","software","People repeating document workflows","Generate editable outputs",("license","subscription"),("coding","writing","design"),("global","ZA"),0,6,3,4,3,3,4,2,"Test a narrow template with five users."),
("education-exam-practice","Exam practice packs","education","Learners preparing for a defined exam","Create original questions and explanations",("digital-products","subscription"),("education","writing","research"),("global","ZA"),0,5,4,4,4,4,3,2,"Check syllabus alignment and request educator review."),
("education-language-cards","Language-learning cards","education","Beginner language learners","Sell printable practice sets",("digital-products","subscription"),("education","design","writing"),("global","ZA"),0,4,3,3,3,4,4,2,"Test a sample and measure learner completion."),
("education-teacher-resources","Teacher resource packs","education","Teachers with planning tasks","Provide editable original resources",("digital-products","license"),("education","design","writing"),("global","ZA"),0,5,4,4,4,4,3,2,"Interview teachers about repeated tasks."),
("digital-planning-templates","Niche planning templates","digital-products","A defined role or hobby community","Sell editable planning systems",("digital-products","license"),("design","research","writing"),("global","ZA"),0,4,3,3,3,4,4,2,"Publish a sample and measure qualified interest."),
("digital-operational-checklists","Operational checklists","digital-products","Small operators","Sell practical downloadable guides",("digital-products","service"),("writing","research","design"),("global","ZA"),0,3,3,3,3,5,4,2,"Verify requirements with practitioners."),
("digital-asset-packs","Original design asset packs","digital-products","Creators and small brands","Sell reusable original assets",("digital-products","license"),("design","video"),("global","ZA"),0,5,3,3,3,4,4,2,"Validate a distinct use case and asset rights."),
("physical-printable-kits","Printable activity kits","physical-products","Families and educators","Bundle printable activities",("digital-products","physical-sales"),("design","education","writing"),("global","ZA"),0,4,3,3,3,4,4,2,"Test digital demand before inventory."),
("physical-local-gift-box","Local themed gift bundles","physical-products","Gift buyers and organizations","Curate a local bundle",("physical-sales","wholesale"),("sales","research","design"),("ZA","local"),500,5,3,4,3,3,3,2,"Pre-sell a small batch and calculate full costs."),
("physical-repair-kits","Niche maintenance kits","physical-products","Device or hobby owners","Bundle compatible maintenance supplies",("physical-sales","affiliate"),("research","sales"),("global","ZA"),500,5,3,4,4,3,3,2,"Confirm compatibility, sourcing, and safety."),
("digital-research-briefs","Curated industry research briefs","digital-products","A narrow professional audience","Publish sourced, dated summaries",("subscription","service","digital-products"),("research","writing","analysis"),("global","ZA"),0,5,4,4,4,4,3,2,"Publish a sourced sample and interview target buyers."),
]
OPPORTUNITIES=[Opportunity(*row) for row in _SEEDS]

def match_opportunities(opportunities:Iterable[Opportunity]=OPPORTUNITIES,*,budget=0,hours=5,skills=(),models=(),region="global"):
    if type(budget) is not int or not 0 <= budget <= 10**9 or type(hours) is not int or not 1 <= hours <= 168:
        raise ValueError("Budget must be 0–1000000000; hours must be 1–168.")
    if not isinstance(region, str) or not region.strip() or len(region) > 80:
        raise ValueError("Region must contain 1–80 characters.")
    skills={str(x).strip().lower() for x in skills if str(x).strip()}
    models={str(x).strip().lower() for x in models if str(x).strip()}
    region=region.strip().lower()
    results=[]
    for item in opportunities:
        cost_fit=5 if item.startup_cost<=budget else max(0,5-(item.startup_cost-budget)//500-1)
        time_fit=5 if item.hours_per_week<=hours else max(0,5-(item.hours_per_week-hours))
        skill_fit=3 if not skills else min(5,2+len(skills.intersection(item.skills)))
        model_fit=3 if not models else min(5,2+len(models.intersection(item.models)))
        region_fit=5 if region in {x.lower() for x in item.regions} or "global" in item.regions or region=="global" else 2
        # Only user constraints contribute to the fit score. Seeded market
        # ratings remain visible as hypotheses, not as observed evidence.
        factors={"cost_fit":cost_fit,"time_fit":time_fit,"skill_fit":skill_fit,
          "model_fit":model_fit,"region_fit":region_fit}
        score=round(sum(factors.values())/len(factors)*20,1)
        results.append({**item.to_dict(),"score":score,"score_factors":factors,
          "market_hypotheses_not_scored":{
            "demand":item.demand,"monetization":item.monetization,
            "customer_pain":item.pain,"feasibility":item.feasibility,
            "competition":item.competition,"confidence":item.confidence},
          "score_type":"constraint-fit heuristic; not measured demand, verified profitability, or a revenue forecast",
          "evidence_status":"unverified hypothesis"})
    return sorted(results,key=lambda r:(-r["score"],r["title"]))
