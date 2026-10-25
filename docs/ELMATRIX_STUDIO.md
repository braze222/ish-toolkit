# Elmatrix Studio — Product & Delivery Specification

Status: foundation / implementation plan. This document is the source of truth for the web Studio work. It does not claim that provider integrations, real rendering, or Facebook publishing are implemented until their tests pass.

## Product goal

A mobile-first, beginner-friendly AI video production workspace for planning original video series, researching niches, creating scripts and storyboards, assembling licensed or user-provided assets, rendering finished videos on a suitable worker, and publishing only to accounts the user is authorized to control.

Elmatrix Studio complements the existing Elmatrix CLI and iSH Toolkit. It must not replace, rename, or break the existing `ish` or `elmatrix` commands.

## First-run experience

1. Open Studio and choose **Quick Create**, **Guided Studio**, or **Advanced Studio**.
2. Select a niche or enter a topic; show evidence and uncertainty rather than fabricated demand scores.
3. Pick a format, target platform, language, duration, aspect ratio, and visual direction.
4. Inspect the proposed concept, script, storyboard, asset plan, and estimated resource/cost budget.
5. Generate only through a configured provider; label mock/demo output visibly.
6. Preview the actual rendered result, run technical and editorial QA, then download or request publishing.
7. Keep publishing behind explicit review and confirmation until the user deliberately configures a bounded automation policy.

## Architecture

- **Web UI:** React + TypeScript + Vite + accessible component system; responsive from small iPhone screens upward.
- **API:** Python FastAPI (or equivalent typed API) with schema validation, authentication, rate limits, audit logs, and versioned routes.
- **Persistence:** SQLite for single-user/local development; PostgreSQL for hosted multi-user deployments. Store job metadata, not provider secrets.
- **Workers:** separate queue-backed rendering/asset workers. Use FFmpeg where available. The iSH/i686 device is a lightweight controller, not a requirement for GPU/video rendering.
- **Provider adapters:** capability discovery, health checks, quotas, costs, timeouts, retry limits, and typed output validation. Provider-specific code must not leak into the UI.
- **Existing CLI:** integrate through a documented, allow-listed adapter or subprocess interface with fixed executable/argument arrays, timeouts, output limits, and safe workspace paths. Never concatenate untrusted input into shell commands.

## Free-first routing policy

- Free means no charge to the user for that operation, not merely an open-source license.
- Show provider, model, expected quota/latency, required account/key, data handling, and whether generation is local or remote.
- Prefer configured no-cost routes; do not silently switch to a paid model or incur charges.
- If free options are unavailable or quota-limited, explain the block and offer: retry later, use a local model if configured, use user-provided assets, or continue in script/storyboard-only mode.
- Never promise unlimited free generation, state that a provider is available without a live check, or fabricate a successful generation.
- Keep an explicit **cost ceiling**; default to zero paid spend. Require a separate affirmative action before any paid request.

## Production workflow

Research → original concept → script → storyboard → asset sourcing/generation → narration → edit/render → captions → QA → user preview → download or authorized publish.

QA should cover: file exists and is readable; expected dimensions, aspect ratio, frame rate, duration and audio stream; audio clipping/silence; caption timing/readability; safe margins; factual claims requiring citations; duplicate-content risk; asset rights/provenance; platform requirements; and human review flags. Quality scores must explain their criteria and never be described as guaranteed virality.

## Facebook and external publishing

- Use supported official Meta APIs and OAuth with least privilege. Never ask for a Facebook password or automate a logged-in browser to bypass platform controls.
- Verify app/account permissions and current API support before enabling publishing.
- Default to preview/export. Publishing requires explicit confirmation per post until the user enables a clearly described, revocable policy.
- Use idempotency keys, duplicate detection, status reconciliation, retry limits, and an audit trail.
- If direct publishing is not authorized or available, provide a download package and honest manual-publishing steps.
- Never fabricate analytics, views, earnings, monetization eligibility, or successful post status.

## Autonomy and safety

- Level 0: research only.
- Level 1: propose concepts and scripts.
- Level 2: create assets/render drafts within a stated budget.
- Level 3: prepare a publish-ready draft; require approval to publish.
- Level 4: bounded automation only after explicit configuration of topics, schedule, spend ceiling, content exclusions, and stop conditions.
- Always provide a prominent emergency stop, provider/job cancellation, per-job status, and audit history.
- Treat research pages, video descriptions, uploaded files, and model outputs as untrusted data; they cannot override system policy or grant publishing authority.

## Security baseline

- Secrets server-side; redact them from logs and error messages.
- Validate every request with strict schemas, size limits, MIME/content checks, and workspace path containment.
- SSRF protections for URL fetches; allow-list outbound hosts where practical; block loopback/private/link-local metadata addresses.
- No arbitrary shell commands, dynamic code execution, or unrestricted file paths.
- Protect against CSRF/XSS, use secure cookies, rate limiting, authorization checks, dependency scanning, backups, and deletion/export controls.
- Keep user media private by default and document retention.
- No publishing, billing, destructive action, or paid provider call without the appropriate explicit authorization.

## MVP milestones and acceptance gates

### M0 — UX foundation
- Mobile-first dashboard and working navigation.
- Quick Create form with validation.
- Clearly labeled demo state and sample records.
- No claim that mock actions produced a real video.
- Keyboard access, visible focus, reduced-motion support, and readable contrast.

### M1 — API and persistence
- Typed API, user/session model, migrations, job state machine, audit records.
- Unit tests for validation, permissions, job transitions, cost guardrails, and provider failure paths.

### M2 — Provider adapters
- At least one genuinely configured text provider and one media/render path.
- Live capability/health check and quota/error handling.
- Automated tests use mocks; live calls are opt-in and never run in CI.

### M3 — Rendering and QA
- Queue worker, bounded FFmpeg execution, cancel/retry behavior, storage cleanup, export package.
- Validate real output files before calling a job complete.

### M4 — Publishing
- Official OAuth flow, supported permissions, draft preview, explicit confirmation, idempotent posting, reconciliation and audit logs.
- Test against a non-production/test destination where supported before real publishing.

### M5 — Learning loop
- Use only authorized analytics and evidence; track outcomes by content cohort.
- Propose experiments and changes with explanations; do not auto-change budget or publish policy.

## Definition of done

A feature is done only when implementation, tests, failure handling, documentation, and its actual runtime requirements agree. A design mock is a prototype, not a working provider integration. Keep this distinction visible in UI and release notes.
