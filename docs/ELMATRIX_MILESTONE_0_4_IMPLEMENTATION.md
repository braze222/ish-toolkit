# Elmatrix 0.4 implementation contract

**Target:** turn the 0.3 research foundation into a traceable, evidence-aware opportunity workflow without claiming that hypotheses are proven businesses.

**Scope:** standalone package under `elmatrix-standalone/`. Do not import iSH Toolkit internals or change its installer, commands, vault, TOTP, encryption, or compute behavior.

## 1. Release principles

1. Evidence must be traceable from a claim to a reviewed source observation.
2. A collected article is not proof of demand, customer pain, sales, earnings, or profitability.
3. AI is optional. Core commands, database operations, reports, and tests work offline and without API credentials.
4. External content is untrusted data. Never treat feed text, page text, metadata, or model output as executable instructions.
5. Collection is bounded and explicit. No background crawlers, paywall circumvention, credential-in-URL support, or hidden paid-provider fallback.
6. Nothing publishes, purchases, sends messages, or incurs provider charges without explicit opt-in and a human confirmation step.
7. Scores explain fit and evidence quality separately. A high fit score cannot compensate for missing evidence.

## 2. Recommended data model

Preserve existing tables and migrations. Inspect the live schema before changing it; use additive, versioned migrations and a backup-safe transaction.

### Opportunity
- Stable identifier and slug
- Title, category, target customer, problem hypothesis, proposed offer
- Monetization hypothesis (explicitly not a forecast)
- Startup-cost estimate with currency, range, assumptions, and last-reviewed date
- Estimated weekly hours and required skills
- Target region and intended business model
- Lifecycle state: `hypothesis`, `researching`, `ready_to_test`, `testing`, `validated`, `rejected`, or `stale`
- Created/updated timestamps

### Evidence observation
- Stable ID and content hash
- Source name, source URL, canonical item URL
- Retrieved timestamp and publication timestamp (nullable)
- Query, region, title, and excerpt/observation
- Source type and declared access method
- Collection outcome and parse warnings
- No credentials, cookies, or unnecessary personal data

### Evidence review/link
- Evidence ID and opportunity ID
- Reviewer decision: `supports`, `contradicts`, `context_only`, or `irrelevant`
- Claim type: demand signal, customer pain, competitor offer, pricing, distribution, or other
- Short rationale, reviewer/source, and review timestamp
- Optional numeric observation with unit, period, and methodology
- Review state: `pending`, `reviewed`, or `withdrawn`

A link must never be created automatically just because keywords match. Automated suggestions may be presented as **unreviewed suggestions** only.

### Experiment
- Opportunity ID and falsifiable hypothesis
- Audience, method, offer/prototype, channel
- Budget cap and time cap
- Start/end dates and success/failure thresholds
- Metric definition, result, decision, notes, and evidence links
- Decision: `go`, `iterate`, `stop`, or `inconclusive`

Use foreign keys, parameterized SQL, constraints, and transactions. Keep migrations reversible where practical. Never delete original source observations merely because a review is withdrawn.

## 3. Evidence quality and ranking

Report independent dimensions; do not collapse all meaning into one opaque score.

### Fit score
A heuristic for how well an opportunity matches the user's stated budget, time, skills, business model, and region. Document each factor and its scale.

### Evidence confidence
Must be low/unknown when evidence is absent. Increase confidence only when there are relevant, human-reviewed observations with traceable provenance. Consider:
- relevance to the exact claim
- source quality and transparency
- freshness and publication date
- independence (syndicated copies count as one underlying source)
- corroboration and contradiction
- whether the observation is direct or merely a proxy

Do not count the number of articles as the number of independent sources. Do not infer purchase intent from generic attention. Do not infer revenue from prices or follower counts.

### Market signal status
Use explicit statuses such as `no_evidence`, `weak_signal`, `mixed_signal`, `corroborated_signal`, and `stale_evidence`. Document that these statuses indicate research support, not a guarantee of business success.

### Required report fields
For every opportunity show:
- fit score and its factor breakdown
- evidence confidence/status and evidence coverage
- strongest supporting observation(s)
- counter-evidence or source disagreement
- missing information
- source links and relevant dates
- assumptions and next validation step
- a clear disclaimer if demand or profitability is unverified

Never show an unverified revenue figure as a fact. If a value is estimated, label it as a scenario, state assumptions, and show the calculation.

## 4. Security requirements

- Parse feeds with size, item-count, redirect, and timeout limits.
- Validate schemes and destinations; allow HTTP(S) only where appropriate. Reject embedded credentials and unsafe local/private-network targets, including redirects that resolve to local services. Revalidate every redirect and resolved destination to reduce SSRF risk.
- Avoid forwarding secrets in URLs, logs, exceptions, reports, or exports.
- Use parameterized SQL and test malformed/oversized values.
- Escape untrusted content when rendered in HTML; do not inject raw feed HTML into the dashboard.
- Keep the dashboard bound to loopback by default. Add request-size limits, safe path handling, and no state-changing GET endpoints.
- Use explicit timeouts and bounded response reads. Handle invalid encodings and malformed XML safely.
- Pin or constrain dependencies only when justified; run dependency and static checks where available without requiring network in unit tests.
- Treat any AI-provider adapter as an external data disclosure boundary. Require opt-in, disclose what will be sent, minimize payloads, and never send local database contents by default.
- Add prompt-injection fixtures: feed content that says to reveal secrets, change system behavior, execute commands, or disregard rules must remain inert quoted evidence.
- Do not claim the tool is secure solely because it passes unit tests.

## 5. CLI and dashboard acceptance

Keep commands explicit and help text current. Proposed additions:

- `elmatrix review <evidence-id> --opportunity <id> --decision supports|contradicts|context_only|irrelevant --claim-type <type> --rationale "..."`
- `elmatrix links --opportunity <id>`
- `elmatrix report --opportunity <id>`
- `elmatrix experiment create --opportunity <id> ...`
- `elmatrix experiment list`
- `elmatrix experiment record <id> ...`

Exact argument design should follow the existing CLI conventions after inspecting the code. Avoid implementing both a CLI and dashboard workflow twice if a shared service function can support both.

Dashboard should remain read-only until a reviewed write workflow is explicitly designed. If review forms are added, use POST, validate input, protect against cross-site requests as appropriate, and show confirmation before writes.

## 6. Test matrix

All tests below must run offline with temporary databases and deterministic fixtures.

### Data integrity
- Schema migration from a database created by the prior release
- Rollback on migration/write failure
- Foreign-key behavior and duplicate source suppression
- Evidence review cannot reference missing records
- Withdrawn review does not erase original observation

### Evidence logic
- No evidence yields unknown/low confidence, not a positive signal
- Contradictory sources remain visible
- Old evidence is marked stale
- Syndicated/duplicate items do not count as independent corroboration
- Unreviewed keyword matches do not affect evidence confidence
- Every report claim links to reviewed evidence or is labeled a hypothesis

### Network and parser safety
- Invalid scheme and embedded credentials rejected
- Oversized body and excessive entries bounded
- Timeout, redirect loops, and non-success status handled without fake success
- Redirect to localhost/private/link-local destinations rejected
- Malformed XML and invalid character encodings handled safely
- Prompt-injection text stored/rendered as inert content
- Dashboard HTML escapes titles, URLs, and excerpts

### CLI, UX, and portability
- Help and exit codes for every command
- Stable JSON export and valid CSV quoting
- Database errors do not expose secrets
- Offline operation with no API keys
- Python versions supported by the package
- Existing iSH Toolkit tests and commands remain unaffected

## 7. Definition of done

- [ ] Current branch, PR, CI results, and existing schema audited before edits.
- [ ] Existing tests pass before feature changes; failures recorded rather than hidden.
- [ ] Versioned migration and backup/recovery notes are present if schema changes.
- [ ] Evidence reviews and experiment results are persisted and exportable.
- [ ] Reports distinguish user-fit, evidence quality, assumptions, and unknowns.
- [ ] Security regression tests pass.
- [ ] Full standalone test suite and CLI smoke tests pass.
- [ ] CI status is inspected after the final commit; no claim of success based only on a local run.
- [ ] README and roadmap accurately describe implemented vs planned capabilities.
- [ ] Diff reviewed for unrelated changes, secrets, unsafe network behavior, and toolkit coupling.
- [ ] PR remains unmerged unless the repository owner explicitly chooses to merge it.

## 8. Execution order

1. Audit branch, PR, CI and current database/CLI/dashboard implementations.
2. Run existing tests and capture baseline.
3. Add schema migration and data-model tests.
4. Implement reviewed evidence links and shared service functions.
5. Add evidence-quality and staleness logic with deterministic tests.
6. Add experiment persistence and CLI workflow.
7. Harden network destination validation and dashboard output escaping.
8. Update reports, exports, docs and examples.
9. Run full tests, smoke tests, security cases, and CI.
10. Review final diff and report exact commit, test, CI, and known-limit status.

Do not attempt every future AI, scraping, or publishing integration in this milestone. A small verified evidence loop is more valuable than a broad but untrustworthy feature set.
