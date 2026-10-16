# Maintainer security checklist

## Automated in repository configuration

- Python 3.10/3.12/3.13 test matrix with read-only workflow permissions.
- Actions pinned to commit SHAs and checkout credentials not persisted.
- Security workflow: common secret-pattern checks on tracked files and reachable
  history, plus pip-audit of resolved runtime/development dependencies.
- Weekly dependency and GitHub Actions update proposals through Dependabot.
- Public issue template discourages posting credentials or vulnerabilities.

A passing pattern scan is limited evidence; it misses unknown token formats,
encoded/encrypted credentials and secrets without recognizable signatures.
Dependency audits cover the resolver result on CI, not packages installed on a
user's iPhone. Requirements express compatibility floors, not a declaration
that every old permitted dependency is free of known vulnerabilities.
Review update PRs and passing tests; do not enable blind automatic merging.

## GitHub settings still require owner action

The available integration can update repository files but cannot configure
account security, repository rules, or private-reporting settings. These are
not enabled merely by committing this checklist:

1. Protect the owner account with a passkey or 2FA and store recovery codes.
2. Enable private vulnerability reporting under repository security settings.
3. Enable secret scanning and push protection where GitHub offers them.
4. Enable Dependabot alerts and security updates where available.
5. Protect main with a ruleset: require pull requests and the test/security checks,
   block force pushes/deletion, and require review where another reviewer exists.
6. Review collaborator access, installed apps, tokens and SSH keys; remove unused
   access. Prefer narrowly scoped, expiring tokens.
7. Review GitHub email privacy and use your provided noreply address for future
   commits if desired. Existing commit metadata can contain a public email;
   changing a setting does not rewrite existing history.

Do not enable required reviews that nobody can supply without planning how to
maintain the project. Keep owner recovery access independent of this toolkit.

## Before wider promotion

Confirm the exact commit's CI is green, run the new build on iSH, test recovery
with dummy data, publish known limitations, and seek independent security review.
Until then, describe it as an early release for testing and feedback. Never claim
that it is audited, unhackable, certified or a guaranteed replacement for a
mature password manager.

References:
- https://docs.github.com/en/code-security
- https://github.com/pypa/pip-audit
