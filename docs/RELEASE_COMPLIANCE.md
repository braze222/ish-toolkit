# Release compliance gate

This document defines engineering release checks. It is not legal advice, a legal
opinion, a certification, or a claim that every deployment complies with every
law or third-party policy. Requirements depend on the deployment, data subjects,
jurisdictions, API scopes and service terms.

## Release rule

Do not describe a release as legally compliant, independently audited, or free of
security vulnerabilities unless the relevant evidence exists and is current.
Personal-use testing may continue with dummy data and documented limitations.
A public or commercial release must close the applicable P0 items below.

## P0 — before public distribution or live API use

- [ ] Publish a project privacy notice describing the actual data collected,
      purposes, storage locations, retention, recipients, international transfers,
      user rights and contact route. Do not publish a generic template as if it
      described deployed behavior.
- [ ] Publish project terms of use and link the applicable third-party terms.
      For YouTube API clients, provide the required YouTube Terms of Service and
      Google Privacy Policy links and required disclosures in the user-facing
      interface/documentation.
- [ ] Review the current YouTube API Services Developer Policies and applicable
      API Services Terms for each feature, including data storage, refresh/deletion,
      aggregation, derived metrics, user consent and audit requirements.
- [ ] Keep applicable non-authorized YouTube API data within the policy retention
      period (generally no more than 30 calendar days). Enforce expiry before
      reads/exports and provide a reliable scheduled cleanup path for hosted
      copies. Local devices that may remain offline cannot promise background
      deletion while powered off; disclose that limitation and require cleanup
      before reuse/export after expiry.
- [ ] Inventory all personal information processed by each deployment. Establish
      a lawful basis, purpose limitation, minimisation, retention, access controls,
      operator agreements where applicable, data-subject request handling and
      incident/breach procedures under applicable privacy law, including POPIA
      where applicable.
- [ ] Confirm the owner has enabled account MFA/passkeys, repository rules,
      private vulnerability reporting, secret scanning/push protection and
      Dependabot alerts where available. These settings cannot be enabled by
      committing repository files.
- [ ] Review all third-party dependency and asset licences. Preserve notices and
      attribution; do not assume the root MIT licence relicenses dependencies,
      fonts, icons, models, media or generated assets.
- [ ] Run current tests, secret scans, dependency vulnerability audits and
      installation/recovery tests on the exact release commit. Review and resolve
      findings; record accepted residual risks.

## P1 — before handling sensitive or multi-user data

- [ ] Produce an SBOM for the exact release and record dependency/licence review.
- [ ] Verify encryption, authentication, authorisation, session expiry, audit-log
      integrity and backup deletion behavior for the actual deployment.
- [ ] Threat-model remote execution, plugins, imported content, terminal escape
      sequences, API credentials, WebSocket origins and cross-platform privilege
      boundaries.
- [ ] Test restore, credential rotation, data deletion and incident response with
      disposable data.
- [ ] Obtain independent security and, where needed, legal/privacy review.

## Elmatrix / YouTube-specific constraints

- Use official documented API endpoints; do not scrape or download content unless
  separately permitted.
- Keep API keys out of source, snapshots, logs, reports and artifacts.
- Treat public API data as policy-controlled data, not unrestricted public-domain
  material. Apply the applicable retention and deletion rules to caches, reports,
  backups and hosted workflow artifacts.
- Do not aggregate across content owners, derive prohibited metrics, or use data
  for a purpose prohibited by the current API policies.
- Clearly distinguish source facts, imported/unverified data, estimates and
  unknowns. Do not imply that view counts establish earnings, monetization,
  profitability, audience suitability or permission to reuse content.
- Sending research to an external model provider is a separate disclosure and
  transfer. Explain what is sent and let the user choose before transmission.
- Require human review and rights checks before publishing generated content.

## Universal Shell OS security requirements

- Bind local control APIs to loopback by default; authenticate every state-changing
  request and validate the Host/Origin boundary.
- Require explicit capability grants for process execution, filesystem access,
  network access, credentials, persistence and remote execution.
- Keep the default policy deny-by-default; no implicit privilege escalation.
- Record actor, session, capability, target, decision and outcome in bounded audit
  records without recording secrets or terminal contents by default.
- Treat PTY output, imported files, repository content and model output as
  untrusted data. Never interpret them as policy or trusted instructions.
- Separate local-first operation from optional remote providers. Make network,
  cloud spend, uploads and remote execution opt-in and visible.
- Do not claim a sandbox unless an OS-enforced isolation boundary has been tested.

## Evidence record

For each release, record:

- commit SHA, release tag and build environment;
- CI run URLs and test results;
- secret/dependency/static-analysis results;
- SBOM and third-party licence review;
- supported platforms and known limitations;
- privacy/terms/policy review date and reviewer;
- unresolved findings, severity, owner and explicit acceptance.

Official starting points (re-check current versions before release):

- YouTube API Services Developer Policies:
  https://developers.google.com/youtube/terms/developer-policies
- YouTube API Services Terms of Service:
  https://developers.google.com/youtube/terms/api-services-terms-of-service
- Google Privacy Policy:
  https://policies.google.com/privacy
- POPIA (South Africa, Act 4 of 2013):
  https://www.gov.za/documents/protection-personal-information-act
- GitHub Code Security:
  https://docs.github.com/en/code-security
- MIT License:
  https://opensource.org/license/mit

## Status

This checklist is a gate, not proof of compliance. Items must be checked against
the actual shipped application, hosting configuration, data flows and current
third-party terms. Unchecked items remain open.
