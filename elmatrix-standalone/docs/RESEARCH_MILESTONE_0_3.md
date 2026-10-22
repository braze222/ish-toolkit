# Elmatrix research milestone 0.3 — implementation notes

## Delivered in this preview
- RSS/Atom feed adapter using Python standard library.
- Explicit opt-in collection command; no scheduled/background fetching.
- HTTP(S)-only URLs, no URL-embedded credentials, bounded timeout and response size, bounded item count.
- Canonical URL cleanup for common tracking parameters and content-hash duplicate suppression.
- SQLite evidence ledger with provenance and timestamps.
- Evidence-aware report that does not treat generic feed entries as evidence for any particular niche.
- Offline tests for URL validation, parsing, deduplication, and honest ranking labels.

## Not yet delivered
- Automatic evidence-to-niche linking and relevance review UI.
- Verified market-demand data, current trend metrics, or competitor revenue.
- Multiple specialist API adapters, semantic clustering, source disagreement analysis, or stale-data weighting.
- LLM-based briefs/content creation or publishing.

## Next acceptance gate
Do not increase a niche's evidence score until an observation is explicitly linked to that niche and its claim, the source is relevant and independent, the observation date and metric are available, and conflicting evidence can be represented. Any future AI output must quote/paraphrase only as permitted, cite the exact source, label uncertainty, and require human approval.
