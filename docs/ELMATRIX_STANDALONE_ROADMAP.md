# Elmatrix standalone — milestone 0.3

## Status: research foundation implemented; intelligence features remain staged

Elmatrix lives under `elmatrix-standalone/` and remains separate from the iSH Toolkit runtime, installer, security utilities, and compute commands.

### Implemented in this branch
- Standalone Python package metadata and `elmatrix` CLI entry point.
- Broad starter catalog spanning content, services, software, education, digital products, and physical products.
- Transparent heuristic profile matching by budget, time, skills, business model, and region.
- Explicit opt-in public RSS/Atom collection using bounded HTTP requests.
- Evidence ledger in SQLite with source/feed URL, canonical item URL, retrieval timestamp, publication timestamp when available, query, region, observation, and content hash.
- URL canonicalization and duplicate suppression.
- CLI commands for `research`, `evidence`, `report`, `match`, `experiment`, and `export`.
- Loopback-only read-only dashboard for matching, catalog browsing, and evidence inspection.
- Offline unit tests and a CI workflow across Python 3.10–3.13.

### Research integrity rules
- A feed item is an observation, not proof of demand, sales, revenue, or profitability.
- Feed entries are not automatically attributed to a niche; current reports explicitly show unverified evidence coverage until reviewed links exist.
- Network failures return an error rather than a fake successful report.
- No unbounded crawling, credential-in-URL support, hidden provider fallback, automatic publishing, or background collection.
- The dashboard binds to `127.0.0.1` only.

## Remaining milestone work

1. **Reviewed evidence links:** add explicit evidence-to-opportunity and evidence-to-claim relationships, with a human relevance decision and rationale.
2. **Competitive comparisons:** compare only public, source-linked offer details and observable content signals; keep source disagreement and collection dates visible.
3. **Evidence quality:** add stale-data warnings, source independence/quality indicators, metric definitions, missing-data display, and counter-evidence.
4. **Live source diversity:** add another source adapter only after documenting API terms, access limits, and data semantics. Keep fixtures for offline CI.
5. **Evidence-aware ranking:** do not increase a niche score from generic feed volume. Use only reviewed relevant evidence and expose the factors, uncertainty, and evidence coverage.
6. **Optional AI research briefs:** provider-neutral, explicit opt-in, cited claims, source-text prompt-injection handling, and human review.
7. **Original content workflow:** create drafts only after evidence quality checks; include source attribution, originality and rights review, and approval before publication.

## Acceptance gates
- Tests run without network access or API credentials.
- Every collected item retains a canonical URL and retrieval timestamp.
- Source text is treated as untrusted data and never as instructions to the software or model.
- Failed, stale, contradictory, or missing data is visible and is not converted to positive evidence.
- Revenue and monetization are never reported as facts without direct, authorized evidence.
- No public publishing, purchases, or paid provider calls happen without explicit opt-in.
- The standalone package installs without importing iSH Toolkit internals.

This roadmap distinguishes delivered code from planned work; it does not claim full competitive intelligence, verified market demand, AI content generation, or publishing are already implemented.
