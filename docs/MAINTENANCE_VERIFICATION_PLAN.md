# Maintenance and Verification Plan

**Status:** proposed maintenance gate for the 3.0.2-preview line  
**Scope:** iSH/Alpine compatibility, installer recovery, vault safety, remote compute boundaries, and Elmatrix research integrity.

This document is a verification plan, not a claim that every check has already passed. Keep checks marked **NOT TESTED** until their commands complete successfully in the relevant environment.

## 1. Safety rules

- Work on a dedicated branch or disposable clone. Do not overwrite the user's active working tree.
- Do not run `git reset --hard`, `git clean -fd`, or an unconditional pull as a maintenance shortcut.
- Preserve existing `.pre-*` recovery files until their contents are reviewed and a verified replacement backup exists.
- Never initialize, migrate, or overwrite a live vault as part of a routine test.
- Use disposable directories, synthetic secrets, and temporary SQLite databases for regression tests.
- Do not merge dependency or feature branches solely because CI is green; check the relevant platform and feature matrix.
- Do not report skipped or unavailable checks as passing.

## 2. Baseline checks

Run from the repository root:

```sh
python3 -m compileall -q scripts tools lib tests
python3 -m unittest discover -s tests -p 'test_install_rollback.py' -v
python3 tools/ish-verify.py --quick
git diff --check
```

Record each command's exit status separately. A successful syntax check does not establish runtime correctness. The quick verifier currently excludes vault cryptography and artifact retrieval; retain that distinction in reports.

## 3. Installer rollback

The rollback suite should cover:

- Backup creation failure before launcher replacement.
- Failure on each launcher replacement, including a failure immediately after a filesystem operation.
- Restoration of regular files, symlinks, and previously absent targets.
- Rollback failure with an explicit recovery-backup location.
- Repeated installation and interrupted installation in disposable directories.
- Destination paths that unexpectedly resolve to directories.
- Preservation of file modes and clear recovery instructions.

After changing rollback behavior, run the focused regression suite and `git diff --check`. Do not delete recovery backups automatically.

## 4. Vault and cryptographic safety

- Verify permissions and database integrity without printing secret values.
- Test encryption/decryption and password rotation only with a disposable vault and synthetic test records.
- Include TOTP records in rotation tests; verify that migrated records can be decrypted and generate valid codes.
- Test interrupted rotation and recovery from a separately verified backup.
- Do not change the installed cryptography version on iSH until wheel/build availability and compatibility are established for the target architecture.
- Keep the legacy migration path separate from routine verification. Never reinitialize a working vault to make a test pass.

Mark cryptographic checks **NOT TESTED** unless they were actually exercised.

## 5. Remote compute and artifact retrieval

- Keep planning separate from execution; remote execution, secret delivery, and unknown-cost operations must require explicit permissions.
- Verify SSH host keys independently; do not silently accept changed or unknown host keys.
- Bound output sizes and execution time; sanitize logs before persistence.
- Exercise artifact retrieval only in a disposable environment after investigating iSH syscall compatibility.
- Do not claim cloud-console or remote-host compatibility until tested against the actual provider/account and supported runtime.
- Do not treat a successful local compute test as proof that remote execution or artifact retrieval works.

## 6. Elmatrix research integrity

- Keep scheduled research opt-in, documented, and disableable.
- Treat discovered content as untrusted input. Bound network reads and timeouts, canonicalize URLs, suppress duplicates, and reject private/local destinations on initial requests and redirects.
- Preserve query provenance, source URL, retrieval timestamp, publication timestamp when available, and review decisions.
- Distinguish opportunity hypotheses from observations and independently reviewed evidence. Never imply that a scan proves demand, income, or profitability.
- Ensure unavailable providers and malformed responses fail safely without corrupting the evidence ledger.
- Test repeated scans, interrupted writes, expired records, duplicate source IDs, and withdrawn reviews.
- Keep OpenCode/provider assistance isolated from secrets and private local data; external use must be explicit and documented.

## 7. Dependency updates

Review each update independently:

- **Paramiko:** verify host-key policy, authentication, transport cleanup, and supported Python versions.
- **cryptography:** verify supported wheels/build paths for the target architecture before upgrading iSH.
- **argon2-cffi:** test installation and hashing in supported environments.
- **pyotp:** run TOTP generation and verification tests.
- **pytest:** run the complete test suite across the supported Python matrix.
- **actions/upload-artifact:** verify the selected runner, action compatibility, permissions, and artifact retention behavior.

Pin reviewed GitHub Actions to verified immutable commit SHAs where practical, and document the review source. Do not loosen security checks merely to make CI pass.

## 8. Release gate

Before tagging or publishing a release, record:

- [ ] Working-tree state reviewed; recovery copies preserved.
- [ ] Syntax and focused regression tests pass.
- [ ] Full supported CI matrix passes.
- [ ] Security workflow passes and findings are reviewed.
- [ ] Vault cryptography and TOTP rotation tested using disposable data.
- [ ] Artifact retrieval tested or explicitly marked unsupported/not tested.
- [ ] Installer tested from a fresh disposable source directory.
- [ ] Documentation matches actual commands and limitations.
- [ ] Release artifacts contain no secrets, private keys, local databases, or personal research data.
- [ ] Remaining warnings, platform exclusions, and untested paths are listed in release notes.

A release is not ready merely because the quick checks pass. The final report must distinguish **PASS**, **FAIL**, **WARNING**, and **NOT TESTED** for every material subsystem.
