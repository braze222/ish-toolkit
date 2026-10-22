# Elmatrix Standalone 0.4.0-preview

A separate niche-opportunity research prototype. This project is intentionally **not integrated** into iSH Toolkit commands, installation, vault/TOTP/encryption, or compute modules.

## Included now

- 23 starter opportunity hypotheses across content, services, software, education, digital products, and physical products.
- Personal fit ranking by budget, available time, skills, business models, and region.
- Explainable score factors; seeded catalog items are hypotheses, not verified market findings.
- Source-linked RSS/Atom research collection with bounded request timeout, a 2 MB feed limit, a bounded item count, URL canonicalization, duplicate suppression, and public-address destination checks for initial URLs and redirects.
- Local SQLite evidence ledger with source/feed URL, canonical item URL, retrieval time, publication time when available, query, region, and observation.
- Evidence-aware JSON report and CSV/JSON catalog export.
- Human-reviewed evidence-to-opportunity links with support/contradiction/context decisions, claim types, rationale, and review withdrawal without deleting source records.
- Report coverage shows reviewed linked observations separately from heuristic fit; reviews do not automatically prove demand.
- Loopback-only browser dashboard.
- Standard-library runtime; tests can run offline.

## Install and run

Python 3.10+; no runtime third-party dependencies.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
elmatrix init
elmatrix niches
elmatrix match --budget 0 --hours 5 --skills writing,research --region ZA
elmatrix research --feed 'https://example.com/feed.xml' --name 'Example public feed' --query 'sample niche' --region ZA
elmatrix evidence --limit 20
# Review an observation after inspecting its source and relevance.
elmatrix review 1 --opportunity content-short-tutorials --decision supports --claim-type demand_signal --rationale 'Explain why this source is relevant.'
elmatrix links --opportunity content-short-tutorials
elmatrix report
elmatrix export --format csv --output niches.csv
python -m elmatrix.server
```

Replace the example feed with a public RSS/Atom endpoint you are permitted to access. A successful feed fetch only records published items; it does **not** establish demand, sales, earnings, or profitability. Network failures exit with an error rather than returning a fake successful report.

Dashboard: http://127.0.0.1:8765. The HTTP server binds to 127.0.0.1. Do not expose it publicly without authentication, request hardening, and a security review.

## Evidence interpretation

Research records are observations, not automatic niche validation. The current version deliberately does not map a general feed item to a niche automatically: that link requires a human review to avoid fabricated relevance. Unreviewed feed items remain unverified. Use `elmatrix review` only after inspecting the source and deciding what claim it supports or contradicts. `elmatrix links` lists reviewed links, and `elmatrix withdraw-review ID` withdraws a review while retaining the original observation. A reviewed link improves traceability but is not statistical proof of demand.

## Roadmap

1. Source-linked RSS/Atom observations and a local evidence ledger (implemented in this preview).
2. Human-reviewed evidence-to-opportunity links, stale-source warnings, and competing-source comparison.
3. More live source adapters after checking current terms, quota and API availability.
4. Provenance-aware ranking based on relevant linked evidence, not generic article counts.
5. Optional provider-neutral AI research briefs with claim-to-source citations.
6. Original content outlines/drafts with rights, originality, safety, and human-approval checks.
7. Publishing integrations only as an explicit opt-in feature with permissions and review.

## Tests and safety

```sh
python -m unittest discover -s tests -v
```

No API keys, telemetry, background collection, AI calls, public posting, or paid services are configured by default. Do not put credentials or sensitive personal data in research notes.
