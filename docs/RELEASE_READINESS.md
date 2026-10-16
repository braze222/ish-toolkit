# Release readiness: 3.0.1 preview

Reviewed 2026-10-17 (South Africa). This records known remaining work rather than
implying that every possible issue has been eliminated.

## Verified

- Main includes the original security toolkit, compute preview and compatibility
  update; no vault-format or KDF downgrade was made.
- Compatibility build: 171 tests passed locally, including the opt-in SSH round
  trip and a fresh control-only venv without crypto packages.
- GitHub tests and security baseline passed for compatibility commit `096400e`.
- Python 3.10/3.12/3.13 CI and the separate Python 3.12 loopback SSH test are enabled.
- Current installation, upgrade, compatibility and compute guides are linked from
  README. The older PDF remains explicitly labeled as the 2.1 offline handbook.
- Reviewed upstream checkout 7.0.1 and setup-python 7.0.0 releases; updated all
  three workflows to their verified immutable commit SHAs. No removed setup-python
  `pip-install` input was in use; no `pull_request_target` trigger is configured.
  Check the maintenance commit's own Actions results before treating it as passed.

## Dependency-update decisions

Dependabot PRs 1/2 proposed the Actions upgrades applied in this review. Python
PRs 3–6 propose raising **minimum allowed versions** of cryptography, pytest,
pyotp and argon2-cffi. The existing ranges already permit their newer releases;
pip installs the newest compatible resolution by default. Raising every floor
is not the same as updating an installed iPhone and can exclude Alpine's available
prebuilt packages. Those floor changes remain deferred for compatibility review;
they are not silently merged or represented as resolved security findings.

A low compatibility floor does **not** certify old versions as safe. The CI
requirements audit checks the newly resolved dependency set, not packages already
installed on a user's device. Review the actual installed package versions and
Alpine security updates before important secrets are used. Where an official
`pip-audit` installation is available in the same interpreter environment, run
`python -m pip_audit` to audit that installed environment. Do not use a successful
latest-resolver audit as proof that an old phone's packages are current.

## Outstanding validation and administration

| Item | Status / evidence needed |
|---|---|
| Older iOS 16 phone | Failure reported; model, iSH/Alpine/Python versions and exact error still needed. Run `sh scripts/compatibility.sh` on updated source. |
| Other iPhone generations | No blanket physical-device verification. Passing runtime/self-tests is required for each environment. |
| Live GitHub CLI dispatch | API doubles and repository CI tested; authorized dispatch/status/logs/artifact/cancel end-to-end still needed. |
| Production SSH server | Real loopback protocol tested with userspace fixture; representative real OpenSSH Linux hosts remain to validate. |
| Real Docker | Restrictive command assembly tested; engine/image and interrupted cleanup remain to validate. |
| Cloud-console bootstrap | Implemented; actual Google/AWS/Azure sessions remain to validate. |
| Account/repository protections | MFA, branch/ref rules, private reporting and push protection require owner-admin verification. Code/docs do not turn those settings on. |
| Independent security review | Not performed; automated tests/scans do not certify absence of vulnerabilities. |
| Updated printable compute book | Detailed Markdown compute/compatibility guides are current; the existing PDF covers only the historical offline tools. |

No open ordinary GitHub issues were returned during this review. Dependency PRs
are tracked separately above. An empty issue list is not evidence that there are
no bugs. Continue using the preview with dummy data and independent recovery copies
until the relevant device/provider gates have passed.

Upstream release references:
- https://github.com/actions/checkout/releases/tag/v7.0.1
- https://github.com/actions/checkout/releases/tag/v7.0.0
- https://github.com/actions/setup-python/releases/tag/v7.0.0

Updating Actions pins also changes the reviewed `ish-job.yml` contract. Update
both the local checkout and configured reviewed remote commit before dispatching;
an older client's byte-for-byte contract check should reject the changed workflow.
Do not bypass that check to make mismatched versions run.
