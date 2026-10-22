# Elmatrix standalone — next development milestone

## Milestone 0.3: source-linked niche research and competitive intelligence

**Goal:** move from a locally seeded opportunity catalog to a research workflow where each important market claim can be inspected, dated, and challenged. Elmatrix remains a separate project; it must not become an `ish` subcommand or depend on iSH Toolkit internals.

### 1. Live, source-linked research
- Add pluggable public-source adapters, starting with sources whose access terms and API limits permit the intended use.
- Store source name, canonical URL, retrieval timestamp, query/region, metric definition, and a short factual observation for every evidence item.
- Keep source facts distinct from user hypotheses, imported data, and AI-generated summaries.
- Set explicit timeouts, bounded result counts, respectful rate limits, and clear source/API-key requirements. No stealth scraping, access-control bypass, or unbounded crawling.
- Provide offline fixtures so tests do not require API keys or network access.

### 2. Competitive intelligence
- Compare public offers, audience questions, content formats, visible engagement signals, pricing when explicitly published, and gaps users report.
- Treat view counts and engagement as observations, not proof of demand, earnings, conversion, or competitor profitability.
- Deduplicate URLs, retain provenance, and show when sources disagree or data is stale.
- Do not copy protected content, impersonate creators, or infer private analytics.

### 3. Evidence-based opportunity ranking
- Explain each score as separate factors: observed demand signals, customer pain, monetization path, feasibility, competition, cost/time fit, and evidence quality.
- Weight evidence by recency, source quality, independence, sample size, and whether the metric directly supports the claim.
- Show uncertainty, missing data, and counter-evidence. Do not turn missing evidence into a positive score.
- Keep a visible separation between measured observations, calculated estimates, and assumptions.
- Require a validation experiment and success metric before marking a niche as validated.

### 4. Optional AI research/content workflow (after research foundations)
- Make model/provider integrations opt-in and provider-neutral. Detect available tools; never claim a model is free solely because a catalog lists zero prices.
- Generate a cited research brief first, then original content outlines/scripts/drafts tied to that evidence.
- Include source links, claim-to-source mapping, originality checks, rights/safety review, and human approval gates.
- No automatic public publishing, spending, credential collection, or hidden provider fallback by default.

### 5. Suggested implementation sequence
1. Define an evidence schema and migration/versioning strategy.
2. Add a source adapter interface plus offline fixture adapter.
3. Implement one well-documented live source adapter after verifying its current API terms and quota model.
4. Add provenance-aware deduplication and stale-evidence warnings.
5. Rework ranking to expose factor values, confidence, evidence coverage, and uncertainty.
6. Add competitive comparison reports and CSV/JSON export.
7. Add opt-in AI-generated cited briefs; content drafts come after evidence quality checks.
8. Add tests for source failures, timeouts, stale data, duplicate sources, missing metrics, prompt injection in source text, and offline behavior.

### Acceptance criteria
- Every live observation has a canonical source URL and retrieval timestamp.
- Network failure never produces a successful-looking empty or fabricated market report.
- Tests run offline and do not need provider credentials.
- Ranking output explains its factors and clearly marks unverified hypotheses.
- No report presents competitor revenue or monetization status as fact without direct, authorized evidence.
- The standalone package installs and runs without modifying toolkit commands, configuration, vault, or compute state.
- The browser interface remains loopback-only unless authentication and deployment security are explicitly implemented.

### Out of scope for this milestone
- Guaranteed income or “profitable niche” claims.
- Private competitor analytics or inferred exact revenue.
- Unbounded scraping, evading quotas, or bypassing paywalls.
- Automatic posting, purchases, ad spend, or autonomous actions with external side effects.
- Coupling Elmatrix to the iSH Toolkit's internal Python modules.

This milestone is a development plan, not a claim that live research adapters or AI content generation already exist.
