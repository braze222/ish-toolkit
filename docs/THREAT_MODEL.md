# Threat model and review scope

## Intended protections

The toolkit is designed to reduce accidental overwrites, unauthorized SQL in
read-only mode, use of corrupted snapshots, incomplete vault password changes,
and exposure of encrypted values while stored. New-key creation uses private
staging, exclusive publication and a stable lock; existing keys are preserved.

## Assumptions

The local account, interpreter, cryptographic libraries, kernel and storage
semantics are trusted. The owner controls the device and stops legacy clients
before migration/recovery. Passwords are strong and recovery material is kept.
The same-user attacker is outside the isolation guarantees of filesystem modes.

## Assets and boundaries

| Asset | Protection | Remaining exposure |
| --- | --- | --- |
| Vault values/TOTP seeds | Argon2id and authenticated encryption | Labels, unlocked process memory, terminal output |
| Crypt private key | Mode 0600; optional encrypted PKCS8 | Raw historical copies; unlocked process memory |
| Backup payload | Checksum, validation, optional authenticated encryption | Unsigned manifest; metadata; temporary plaintext |
| SQLite workspace | Read-only default and explicit write policy | Plaintext on disk; same-account file access |
| Repository | Read-only CI tokens, pinned Actions, scans and update proposals | Unknown vulnerabilities; account compromise; manual review mistakes |

## External review needed

Review cryptographic container design and key lifecycle, symlink/path races,
malicious SQLite/archive handling, resource-exhaustion bounds, recovery during
power loss, and platform-specific filesystem behavior. Process-kill tests are
not a proof of every power-loss scenario. Do not describe this document as an
audit, certification, penetration test or guarantee.

## 3.0 compute extension

Trust additionally includes the explicitly selected host, its administrators,
executed repository/workload, GitHub repository writers, official provider APIs
and installed CLI/runtime dependencies. Verified SSH protects channel identity,
not the remote account against its administrator. Private job directories do not
isolate code from other files owned by the same account.

Controls: strict SSH identity, no agent forwarding, bounded JSON transports,
allowlisted workflow tasks, exact workflow/commit checks, explicit execution and
credential/cost grants, no implicit retry, private metadata, sanitized bounded logs,
no-overwrite artifact publication, archive/path validation and no provisioning.

Residual risks: account compromise; malicious authorized commands; secret
transformation/exfiltration; partial artifact folders; stale measurements; unknown
outcomes after abrupt termination; workers or containers surviving failed cleanup;
provider/ref-policy changes; dependency compromise; iSH syscall differences.
These remain reasons to use dedicated low-privilege environments and independent
backups, not claims of complete cyber protection.
