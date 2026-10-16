# Compatibility across iPhone generations

A phone's iOS version alone does not identify the failing component. iSH provides
an emulated Linux userspace; Alpine release, Python, installed packages, filesystem
behavior, memory pressure and iSH's syscall implementation affect this toolkit.
Linux architecture reported inside iSH is not the phone's physical CPU model.

The official iSH App Store listing reviewed 2026-10-16 states iOS 11 or later:
https://apps.apple.com/us/app/ish-shell/id1436902243
Thus iOS 16 is within the app's listed range. This is **not** evidence that every
feature of this toolkit has passed tests on every iPhone/iOS combination.
iSH's emulator architecture is described at https://ish.app/ and
https://github.com/ish-app/ish . We cannot extend Apple's or iSH's OS support in
Python code or detect the exact iPhone generation reliably from Linux values.

## Choose a profile

| Profile | Requirements | Features |
|---|---|---|
| Full | Python 3.10+, POSIX/fcntl/SQLite, working cryptography/argon2/pyotp, storage self-test | Offline security tools plus compute |
| Control | Python 3.10+, POSIX/fcntl/SQLite, storage/process self-test | Status, console setup, SSH/Actions with official gh credentials, jobs without vault secrets |
| Diagnostics only | Working POSIX shell | Baseline report even if Python/toolkit installation fails |

Control avoids mandatory crypto-package installation and local Argon2 work. It
is not a weaker-encryption vault: secret-reference features remain unavailable
until full dependencies work. Existing vaults, key files, stored configuration
and unrelated launchers are preserved. Existing security-tool launchers from a
previous install are not deleted by switching to control. Keep older source
folders if those launchers still reference them.

The controller and remote worker now use `select` for their small set of pipe
file descriptors, avoiding an assumption that epoll/kqueue works under emulation.
This is a portability change, not proof that epoll caused the reported failure.
No fallback bypasses file locking, fsync, atomic publication or strict SSH keys.
No Argon2 memory/time settings, encryption strength or vault format are reduced.

## Diagnose the failing older phone first

From a checkout of this version:

```sh
sh scripts/compatibility.sh
```

This reads OS/runtime/tool availability and makes no network calls or changes.
It does not print environment credentials, account names, device identifiers,
SSH keys or vault contents. Send the report with the exact failed command/error,
iPhone model, iOS version and iSH app version from Settings. If iSH itself cannot
launch, the toolkit script cannot repair the app; preserve/export the filesystem
before reinstalling or changing apps.

If Python starts:

```sh
python3 tools/ish-compatibility.py
```

Package discoverability is reported separately from successful imports/crypto
execution. The installer verifies actual required imports. Neither report is a
security certification, memory stress test or benchmark.

## Try control mode

Use a separate source checkout, preserving your existing working installation:

```sh
cd ~/ish-toolkit-v3-preview
ISH_PYTHON=python3 sh install.sh --profile control
export PATH="$HOME/.local/bin:$PATH"
hash -r
ish compatibility
ish selftest --control
ish status
```

If your compatible Python is in `/root/venv/bin/python`, use that exact path for
ISH_PYTHON. A missing/stale venv is reported explicitly rather than silently
selecting a different interpreter with different dependencies. Python below 3.10
is not made secure or supported by lowering a version check. Preserve the iSH
filesystem and follow Alpine/iSH's supported upgrade procedure first. Do not mix
stable/edge repositories or run a blind distribution upgrade over a live vault.

Control does not run the crypto/full self-test. To use vault references or offline
security commands, install compatible prebuilt Alpine crypto packages and use
an appropriate venv, following docs/python.md. Then explicitly install full:

```sh
ISH_PYTHON=/root/venv/bin/python sh install.sh --profile full
ish selftest --full
ish vault verify
```

Never reinitialize an existing vault to resolve a dependency problem. Low-memory
or killed crypto operations require diagnosis; reducing the KDF is not a fix.
For older phones, use lightweight local commands and existing authorized SSH
hosts for larger work. iOS background suspension still applies; this release
cannot promise jobs continue while iSH is suspended.

## Support and testing status

- Linux build/CI: Python 3.10, 3.12 and 3.13 are exercised in CI.
- iSH/iOS 16 older phone: failure reported by user; exact error/model unknown.
- Earlier user device: v2.0 self-test was observed passing; not proof for 3.0.1.
- Other generations/iPads: no physical-device certification or blanket promise.
- Native Windows, a-Shell and arbitrary terminal apps: not supported by these
  POSIX/Alpine installation instructions. A compatible authorized remote Linux
  installation may be accessed with a separately configured SSH client.

New regression tests exercise a fresh venv with no third-party packages,
control installation/self-test, secret-reference refusal without dependencies,
read-only diagnostics and process I/O with the default selector disabled.
Physical-device validation remains necessary. Record the phone/iSH/Alpine/Python
combination and exact result before calling that combination verified.

Build-host result for 3.0.1: **171 tests passed in 57.71 seconds**, including
real loopback SSH, the no-third-party-package control install and existing security
regressions. The focused compatibility/installer/compute set passed 50 tests.
These are Linux build-host results, not physical iPhone tests. Shell syntax,
Python compilation and the limited tracked-secret-pattern scan also passed.
