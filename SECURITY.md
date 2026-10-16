# Security policy

This is an early-stage local security toolkit, not an independently audited
password manager. Do not make it the only copy of important credentials or
recovery material. Tests and automated scans do not establish that software is
free of vulnerabilities.

## Reporting a vulnerability

Use the repository's **Security > Advisories > Report a vulnerability** button
when private vulnerability reporting is enabled:
https://github.com/braze222/ish-toolkit/security/advisories/new

If that private option is unavailable, do not post an exploit or real data in
an issue. Open only a content-free request for a private reporting channel and
wait for the maintainer to provide one. A SECURITY.md file does not enable the
GitHub setting, and the project does not claim that this setting has been
verified. Never send production keys, vaults, passwords, seeds or customer data.

Provide the version/commit, affected command, expected/actual result, impact and
minimal reproduction using dummy data. Preserve evidence privately. There is
currently no promised response SLA or bug bounty.

## Maintenance scope

Security fixes target the latest main-branch version. Older packaged builds and
historical installer versions do not receive automatic updates. A GitHub push
does not update an iPhone installation. Follow UPGRADE.md and run the full device
self-test before using new code with live data.

## Trust boundaries

- Supported use is one local user on a device they control.
- Secret values are encrypted; vault labels, backup manifests and ordinary
  SQLite workspaces are not confidential by default.
- Encryption does not protect data while it is displayed or decrypted, or an
  account/device already controlled by an attacker.
- The crypt private key and vault password are distinct recovery requirements.
  There is no lost-key/password bypass.
- Manifests are unsigned. Checksums detect corruption, not replacement of both
  a plaintext payload and its manifest by an attacker.
- Hard termination can leave private temporary plaintext. Flash deletion and
  shred do not guarantee forensic erasure.
- Raw legacy key copies still decrypt ciphertext for the same key identity even
  after a newer copy is password-protected.
- Archive import, custom encrypted containers and crash recovery need external
  security review before high-assurance use.

See docs/SAFE_START.md, docs/THREAT_MODEL.md and docs/MAINTAINER_SECURITY.md.
