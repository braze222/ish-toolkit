"""Evidence-first niche catalog: hypotheses, not verified demand or profit."""
import json

CATALOG = [
 {"id":"local-cleaning","category":"services","name":"Local cleaning lead generation","buyer":"Households, landlords, small offices","offer":"Qualified enquiries or booking pages for local cleaners","query":"cleaning services small business customer acquisition","test":"Interview 5 cleaners about lead sources and missed bookings","risks":"Local competition, travel radius, trust and acquisition costs"},
 {"id":"home-repairs","category":"services","name":"Home maintenance coordination","buyer":"Homeowners, landlords, property managers","offer":"Maintenance intake and vetted-provider directory","query":"home repair maintenance small business","test":"Interview 5 landlords about recurring maintenance jobs","risks":"Provider quality, liability and emergency expectations"},
 {"id":"beauty-booking","category":"services","name":"Beauty appointment tools","buyer":"Independent stylists, barbers and nail technicians","offer":"WhatsApp-first booking, reminders and service menus","query":"salon booking system small business","test":"Ask 5 practitioners how they handle no-shows","risks":"Crowded market, privacy and adoption friction"},
 {"id":"tutoring-leads","category":"services","name":"Tutoring lead generation","buyer":"Independent tutors and parents","offer":"Subject-specific tutor discovery and enquiry pages","query":"private tutoring business finding students","test":"Interview 5 tutors and 5 parents about trust and subject gaps","risks":"Child safety, safeguarding and seasonality"},
 {"id":"small-business-web","category":"digital-services","name":"Simple websites for local businesses","buyer":"Trades, salons, tutors and community businesses","offer":"Fixed-scope mobile website with contact/booking links","query":"small business website design client problems","test":"Audit 20 local listings for missing or broken web/contact paths","risks":"Client acquisition, support scope and commoditization"},
 {"id":"whatsapp-automation","category":"digital-services","name":"WhatsApp workflow setup","buyer":"Appointment-based small businesses","offer":"Opt-in FAQ, lead capture and follow-up workflow","query":"WhatsApp business automation small business","test":"Interview 5 businesses about repetitive questions and response time","risks":"Platform rules, consent and message costs"},
 {"id":"creator-research","category":"creator-tools","name":"Creator niche research briefs","buyer":"Small creators and independent publishers","offer":"Source-linked topic research and editorial briefs","query":"creator content research workflow tools","test":"Ask 5 creators to compare a sample brief with their current workflow","risks":"Data access, platform terms and willingness to pay"},
 {"id":"children-learning","category":"education","name":"Original early-learning activity packs","buyer":"Parents, tutors and educators","offer":"Original printable literacy, numeracy or activity packs","query":"early learning printable worksheets parent teacher","test":"Ask 5 educators to review a sample against one learning goal","risks":"Child suitability, curriculum fit, accessibility and rights"},
 {"id":"exam-revision","category":"education","name":"Exam revision resources","buyer":"Learners, parents and tutors","offer":"Original practice questions, study planners and explainers","query":"exam revision study planner resources","test":"Validate one grade and subject with educators before expanding","risks":"Accuracy, curriculum changes and protected exam materials"},
 {"id":"digital-templates","category":"digital-products","name":"Small-business document templates","buyer":"Freelancers and microbusiness owners","offer":"Editable quote, invoice, onboarding or checklist templates","query":"small business document template pain points","test":"Ask 5 users to complete a real task with a prototype","risks":"Jurisdiction-specific legal/tax needs and free alternatives"},
 {"id":"budget-planners","category":"digital-products","name":"Budget and cash-flow planners","buyer":"Households, students and sole traders","offer":"Simple spreadsheet or printable tracker","query":"budget spreadsheet cash flow template user problems","test":"Test a prototype with 5 users using fictional data","risks":"Trust, sensitive data and free alternatives"},
 {"id":"job-search-kits","category":"digital-products","name":"Job-search organization kits","buyer":"Job seekers and graduates","offer":"Application tracker, interview practice and CV checklist","query":"job search tracker interview preparation template","test":"Interview 5 job seekers and test whether the kit improves follow-through","risks":"No employment guarantee; avoid misleading claims"},
 {"id":"micro-saas-booking","category":"software","name":"Narrow booking and reminder software","buyer":"One specific appointment-based profession","offer":"Small workflow solving one repeated scheduling problem","query":"appointment booking software feature requests small business","test":"Find repeated complaints from 10 independent users before coding","risks":"Security, integrations, hosting and support"},
 {"id":"offline-mobile-tools","category":"software","name":"Offline-first mobile utilities","buyer":"Field workers and users with unreliable connectivity","offer":"Local-first checklist, calculator or record tool","query":"offline mobile app workflow field workers","test":"Observe 5 target users completing the workflow without internet","risks":"Device compatibility, backup/recovery and monetization"},
 {"id":"developer-automation","category":"software","name":"Developer workflow automation","buyer":"Solo developers and small engineering teams","offer":"Focused CLI or repo workflow that saves repeat work","query":"developer workflow automation pain points CLI","test":"Validate with 5 developers against their existing scripts","risks":"Fast-moving tooling, security expectations and maintenance"},
 {"id":"open-source-support","category":"software","name":"Open-source setup and support","buyer":"Small teams needing reliable setup","offer":"Documented onboarding, configuration or maintenance package","query":"open source software setup support small business","test":"Publish a reproducible demo and ask users which setup step blocks them","risks":"License obligations, support burden and conversion"},
 {"id":"home-organization","category":"physical-products","name":"Home organization kits","buyer":"Renters and households with space constraints","offer":"Low-cost organization checklist or locally sourced kit","query":"small home storage organization problems","test":"Price a prototype from real supplier quotes and interview 5 households","risks":"Shipping, inventory, returns and thin margins"},
 {"id":"community-directory","category":"marketplaces","name":"Focused community service directory","buyer":"Residents and independent providers in one locality","offer":"Verified listings for a narrow underserved category","query":"local service directory customer trust problems","test":"Recruit 10 providers and test whether 5 customers can find a match","risks":"Cold start, verification, spam and maintenance"},
 {"id":"career-learning-content","category":"content","name":"Career-skill explainers","buyer":"Learners exploring practical work skills","offer":"Original tutorials with downloadable practice material","query":"career skills beginner tutorial questions","test":"Check recurring questions across sources and publish one original lesson","risks":"Accuracy, outdated advice and platform dependency"},
 {"id":"public-data-guides","category":"content","name":"Plain-language public-service guides","buyer":"People navigating official information","offer":"Source-linked explainers and checklists","query":"how to navigate public services official information guide","test":"Verify each step against official sources and test with 3 readers","risks":"Rules change; do not replace professional advice"},
 {"id":"small-farm-records","category":"software","name":"Simple farm and microbusiness records","buyer":"Small producers and informal operators","offer":"Offline-first stock, expense or harvest tracking template/tool","query":"small farm record keeping spreadsheet challenges","test":"Interview 5 operators; test on paper before building software","risks":"Connectivity, localization, data loss and willingness to pay"},
 {"id":"accessibility-audits","category":"digital-services","name":"Basic website accessibility fixes","buyer":"Small organizations with public-facing sites","offer":"Human-reviewed checklist and prioritized fixes","query":"small business website accessibility common issues","test":"Audit 3 volunteer sites and ask owners which fixes they would fund","risks":"Do not overclaim compliance; expert review may be required"}
]

def get_niche(niche_id):
    return next((item for item in CATALOG if item["id"] == niche_id), None)

def render_catalog(category=None, output_format="markdown"):
    rows = [item for item in CATALOG if category is None or item["category"] == category]
    if output_format == "json":
        return json.dumps({"evidence_status": "hypotheses_not_validated", "niches": rows}, indent=2, ensure_ascii=True)
    clean = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["# Elmatrix niche catalog", "",
             "**Status:** hypotheses only; no demand, profit, price or competitor result is implied.", "",
             "| ID | Category | Opportunity hypothesis | Potential buyer |",
             "|---|---|---|---|"]
    for item in rows:
        lines.append("| {} | {} | {} | {} |".format(item["id"], item["category"], clean(item["name"]), clean(item["buyer"])))
    lines += ["", "Run elmatrix opportunity --niche ID to generate a validation brief."]
    return "\n".join(lines) + "\n"

def render_opportunity(niche_id, region="ZA"):
    item = get_niche(niche_id)
    if item is None:
        raise ValueError("unknown niche ID; run elmatrix niches to list valid IDs")
    query = item["query"].replace("'", "")
    lines = ["# Opportunity validation brief: " + item["name"], "",
        "- **Evidence status:** unvalidated hypothesis; no live market evidence collected by this command.",
        "- **Region:** " + region, "- **Category:** " + item["category"],
        "- **Potential buyer:** " + item["buyer"], "- **Offer hypothesis:** " + item["offer"], "",
        "## First validation steps", "", "1. " + item["test"],
        "2. Find repeated buyer complaints in at least 3 independent public sources; save URLs and dates.",
        "3. Record competitor offers and prices only when directly visible; missing prices stay unknown.",
        "4. Seek a concrete buyer commitment (pilot, waitlist or paid test) before building at scale.",
        "5. Calculate costs from real quotes, including acquisition, delivery, support, fees and tax.", "",
        "## Elmatrix research command", "", "elmatrix scan --query '" + query + "' --region " + region + " --days 14 --limit 20",
        "elmatrix report", "", "## Risks to investigate", "", item["risks"], "",
        "## Evidence ledger", "",
        "| Claim to test | Evidence needed | Status |", "|---|---|---|",
        "| Buyers have this problem | Dated interviews or public source links | Missing |",
        "| Buyers will pay | Pilot, preorder or observable commitment | Missing |",
        "| A reachable customer channel exists | Measured outreach/acquisition test | Missing |",
        "| Unit economics can work | Verified price and cost inputs | Missing |",
        "| Competitors leave a meaningful gap | Actual offer comparison and user complaints | Missing |", "",
        "**Decision rule:** do not call this niche profitable until the evidence ledger is populated and unit economics are calculated from verified inputs."]
    return "\n".join(lines) + "\n"
