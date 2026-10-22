# Elmatrix 0.2.0-preview — scheduled research and explicit assistance

- Daily GitHub research workflow with opt-in activation, explicit demo/live modes,
  bounded requests and seven-day report artifacts; phone need not stay awake.
- Push-triggered demo validates the research pipeline without credentials.
- Explicit OpenCode research assistance with isolated configuration, denied tools,
  bounded execution, fresh zero-token-price checks and no automatic paid fallback.
- No video generation or YouTube publishing. OpenCode model access and live
  scheduled research require the owner's credentials/configuration.

# 3.0.2-preview — transport and artifact failure handling

- Reap transport children when selector setup fails; normalize post-EOF timeouts.
- Handle interrupted/nonblocking pipe operations without leaking raw exceptions.
- Reject non-object GitHub responses and malformed/CRC-invalid artifact archives.
- Accept only stored/deflate ZIP compression before opening member decoders.
- Add nine regression cases; 180 tests passed, including loopback SSH.

See [hardening review](docs/HARDENING_REVIEW.md) for scan findings and remaining
validation limits. This is not a zero-vulnerability certification.

# 3.0.1-preview — older-device compatibility paths

- Add a dependency-light control install and isolated control self-test.
- Add read-only shell/Python diagnostics that do not assume iOS/device detection.
- Use select-based pipe I/O rather than epoll/kqueue in the controller and endpoint.
- Explain missing/old Python and optional crypto dependency failures clearly.
- Preserve full-strength vault encryption, fail-closed storage and existing data.

The reported older iOS 16 failure is not yet reproduced; exact device/error output
is still required. See docs/COMPATIBILITY.md for supported runtime requirements.

# 3.0.0-preview — explicit compute control plane

- Adds private versioned config, strict job validation, explainable backend
  selection, durable job intent/receipts, safe status reconciliation and cancellation.
- Real local and verified SSH execution with bounded redacted logs, private input
  workspaces and constrained artifact retrieval; no implicit shell or resubmission.
- Google/AWS/Azure console discovery, official URLs, diagnostics and reviewed
  user-space bootstrap; no fabricated unattended Cloud Shell API or resource creation.
- GitHub Actions REST adapter for the bundled reviewed workflow, immutable source
  checks, minimal token permissions, safe downloads and explicit unknown-cost grant.
- Restrictive Docker-over-SSH invocation on an already working engine/image.
- Original vault/TOTP/crypt/backup/database formats and commands are preserved.
- New compute guide and explicit validation/remaining-limits record.

This preview is not independently audited. Loopback SSH was tested; live cloud
account dispatch, real Docker and the new runtime on iSH still need validation.

---

# 2.1.1-local security-maintenance update

Validation: 120 local tests passed; resolved runtime/development dependency
audits reported no known vulnerabilities. See docs/SECURITY_CHECKS.md for scope.

- Fixed database initialization on Python 3.10 without disabling normal query policy.
- Private-key creation now uses a stable lock, private staging and exclusive
  publication; rejects symlink/orphan public-key paths and preserves existing
  private identity. A missing public companion can be repaired from that key.
- Added security policy, threat model, safe practice guide, maintainer settings
  checklist, MIT license, dependency audit workflow, update proposals, and a
  limited history/current-file secret-pattern check.
- No claim of an independent audit, full secret detection or automatic device
  protection. GitHub account/security settings require owner action.

# 2.1.0-local | 16 October 2026

Implemented portable backup export/import, guided transactional vault recovery,
password-protected PKCS8 crypt keys, and streaming authenticated file/backup
encryption. Removed historical source copies from the distribution. Updated the
README, upgrade guide, troubleshooting reference and complete user booklet.

The prior iSH EPERM lock fix is included. Permission failures still prevent
entry to protected sections; no lock checks were disabled.

Validation: 116 automated tests passed on the Linux build host. These include
legacy ciphertext compatibility, 34 MiB streaming round trips with measured
Python allocation peak below 16 MiB, altered/truncated stream rejection,
wrong-key and wrong-password refusal, PKCS8 identity preservation, safe bundle
import, duplicate/no-overwrite behavior, and actual child-process termination
before/after recovery transaction commit. Original migration, rotation, SQLite
policy, launcher and CLI tests remain included. Full isolated self-test passed
on the build host. These are engineering tests, not an independent security audit.

The user's 2.0 self-test passed on iSH. Version 2.1 introduces new code and must
run `ish selftest --full` on-device before live key protection or recovery.

Compatibility: working v2 vaults need no migration. New CRYPTv2 encrypted files
require this client. Legacy CRYPTv1 backups up to 32 MiB remain readable. New
stream size cap is 60 GiB; actual usable size depends on iSH storage/performance.
Password-protected key files cannot be opened by old raw-key clients.

Recovery requires the current password when an active v2 vault exists. It is
not a password-reset bypass. A damaged current vault may require manual,
careful preservation and diagnosis; the command fails closed rather than
silently discarding it. No automatic retention/deletion or scheduler was added.

All operations are local. No deployment to the user's device, background
service, remote database, revenue engine or account integration is implied.

# Elmatrix 0.1.0-preview — independent research command

- Adds scan/trends/report/providers and purge with separate private local storage.
- Configurable service and children's-content queries; bounded foreground collection.
- Official YouTube public-data adapter, historical source counts and unknown revenue.
- OpenCode research brief handoff and public zero-token-price catalog discovery.
- Standalone zipapp installer preserves all ish commands/data; CI automatically builds,
  smoke-tests and publishes a deployment bundle after tests. No hosted target implied.
- No video generation, uploads, automatic agent execution or paid model fallback.

## Elmatrix build maintenance — 2026-10-22

- Fix checksum-manifest symlink overwrite through atomic replacement.
- Serialize bundle builds and flush the manifest before publication.
- Exercise the installed research lifecycle independently of the source checkout.
- Verify deployment builds and checksums across Python 3.10/3.12/3.13.
