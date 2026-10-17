# Failure-path hardening review

Reviewed 2026-10-17 for 3.0.2-preview.

## Reproduced failures and fixes

Transport processes that closed stdout but remained alive could raise an unhandled
timeout. Selector setup failure could leave a child process running. Cleanup now
covers setup and execution, reaps the child, closes pipes and reports a bounded,
sanitized error. Interrupted and temporarily unavailable pipe I/O are retried
within the original deadline. Ambiguous execution is not automatically resubmitted.

Malformed ZIP data, CRC failures and unsupported compression previously escaped
artifact handling. They now fail safely before publication. Only stored/deflate
members are accepted; high-memory codecs are rejected before decoder creation.
Existing size, count, path, symlink and exclusive-publication checks remain.
GitHub JSON responses must be objects; invalid types cannot flow into job handling.

## Verification

`ISH_TEST_SSH=1 ../test-venv/bin/python -m pytest -q`: **180 passed in 57.88s**.
The suite includes nine new failure-path cases and a real loopback SSH protocol
fixture. Timeout/setup and malformed-archive regressions were observed failing
before their fixes. No live user vault or cloud account was used.

Bandit 1.9.4 scanned `lib`, `tools` and `scripts`: **0 high, 11 medium, 26 low**
findings. No findings were suppressed. This is a static heuristic scan, not an
independent audit or proof of absence of vulnerabilities.

| Findings | Review disposition |
|---|---|
| 10 medium SQL construction warnings (B608) | Vault identifiers come from fixed secret/TOTP mappings; recovery tables come from a fixed three-table list. Record values are bound parameters. No user-controlled SQL identifier was found in these sites. |
| 1 medium URL-opening warning (B310) | Console reachability uses the internal fixed HTTPS provider URL registry, without credentials. This is an intentional network operation. |
| Low subprocess/import/PATH warnings | Intentional command execution and dispatch; these require trusted executables and hosts. Workloads retain the account's privileges. |
| Low exception-handling warnings | Expected test failures, diagnostic fallbacks and process-exit races require contextual review; they are not a general endorsement of swallowing errors. |
| Low password-literal warnings | One is the boolean recovery-plan field `snapshot_password_becomes_active`; another is a temporary self-test password. Neither is a deployed credential. |

## Remaining limits

Passing tests does not certify every device, dependency version, provider or
failure mode. Physical iOS 16 reproduction, live cloud/Actions dispatch, real
Docker execution, production SSH hosts, repository/account protections and an
independent security review remain listed in
[release readiness](RELEASE_READINESS.md). The compute build remains a preview.
Dependency minimum-version proposals still require compatibility review.
