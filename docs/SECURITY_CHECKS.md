# Security check record - 16 October 2026

This records engineering checks, not an independent audit or security guarantee.

- Local suite: 120 tests passed on the build host, including new key-creation
  refusal/permissions tests and the limited scanner regression.
- Runtime and development dependency resolution: pip-audit 2.10.1 reported no
  known vulnerabilities in the versions resolved on this host at this time.
- Pattern scan: zero findings in 70 tracked files and 66 reachable historical
  blobs before this record was added. Coverage is deliberately limited.
- Previous GitHub CI: Python 3.12 and 3.13 passed. The Python 3.10 initialization
  failure has been addressed by removing the unsupported authorizer-disabling
  call from fixed-statement database creation. New CI results are linked below.
- GitHub main was observed without branch protection. The integration cannot
  enable rulesets, account 2FA or private-reporting settings; see the owner
  checklist. No claim is made that those controls are enabled.
- No on-device 2.1.1 test or independent third-party review has been performed.

## Resolved runtime packages checked

- cryptography 50.0.2
- argon2-cffi 25.1.0
- pyotp 2.10.0
- cffi 2.1.1
- argon2-cffi-bindings 26.1.0
- pycparser 3.11

These are the audited resolver results, not a lockfile or a claim about packages
currently installed on the user's iPhone. New advisories may appear later.

## Current CI results

- https://github.com/braze222/ish-toolkit/actions/workflows/python-package.yml
- https://github.com/braze222/ish-toolkit/actions/workflows/security.yml

## Outstanding review

The threat-model review items, device self-test and recovery drill remain
required before stronger public security claims. Use dummy data while learning.
