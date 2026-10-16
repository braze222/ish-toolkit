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
