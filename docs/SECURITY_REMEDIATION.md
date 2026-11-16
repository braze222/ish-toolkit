# Security remediation plan

**Branch:** security/compliance-remediation-2026-11  
**Baseline:** main at a4f714073feee4c5bd82a5d8d2bb9d4be472a508  
**Status:** documentation and release-gate work; not a completed security audit.

## Confirmed baseline

The repository has a least-privilege security workflow, SHA-pinned GitHub Actions,
non-persisted checkout credentials, secret-pattern checks and pip-audit checks.
The maintainer checklist correctly identifies GitHub account/repository settings
that require owner action. Existing Elmatrix documentation discloses that local
29-day cleanup runs only when commands execute and that an inactive device cannot
delete files while powered off.

## Work in this branch

- Add an explicit release compliance gate covering privacy, API terms, data
  retention, dependency licensing, POPIA considerations and Universal Shell OS
  capability boundaries.
- Preserve the MIT licence and existing security checks.
- Do not weaken authentication, execution permissions, secret handling or
  retention controls merely to remove friction.

## Open engineering findings

1. **Elmatrix retention:** local snapshot expiry is checked when snapshots are
   enumerated, not by a background process while iSH is suspended/offline.
   Hosted workflow artifacts have their own retention configuration; verify the
   exact artifact retention and ensure all copies are covered. Do not promise
   background deletion on iOS.
2. **Policy review:** assess YouTube API aggregation, export, model-provider
   transfer and user-facing disclosures against the current developer policies.
3. **Repository settings:** branch protection/rulesets, MFA, secret scanning,
   push protection, Dependabot alerts and private vulnerability reporting require
   owner-side verification.
4. **Supply chain:** requirements are compatibility constraints, not a complete
   lockfile. Generate an SBOM and review direct/transitive dependency licences.
5. **Universal Shell OS:** the native agent, authenticated API, PTY, WebSocket and
   desktop shell are not established as implemented on public main. Their threat
   model and security tests must precede release claims.
6. **Historical initialization regression:** a prior local test reported that a
   second initialization unexpectedly replaced a token. Reproduce on the current
   working tree and resolve before relying on that initialization path.

## Verification policy

No security finding is closed merely by documenting it. Close findings only with
a code/configuration change, a reproducible test or owner-side evidence. Record
the exact commit and CI run. Do not claim zero risk, legal certification or an
independent audit.
