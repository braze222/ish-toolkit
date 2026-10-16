# iSH Toolkit 2.1.1-local

**Early release, not independently security-audited.** Start with the
[Safe learning guide](docs/SAFE_START.md), use dummy data, and keep independent
recovery copies. Read [SECURITY.md](SECURITY.md) before storing important secrets.

[![Toolkit tests](https://github.com/braze222/ish-toolkit/actions/workflows/python-package.yml/badge.svg)](https://github.com/braze222/ish-toolkit/actions/workflows/python-package.yml)
[![Security baseline](https://github.com/braze222/ish-toolkit/actions/workflows/security.yml/badge.svg)](https://github.com/braze222/ish-toolkit/actions/workflows/security.yml)

An offline command-line toolkit for encrypted secrets and TOTP, local SQLite
workspaces, file encryption, and verified portable backups. Built for the
user's iSH/Alpine workflow. No remote database, autonomous agent, paid service,
background scheduling or new compute execution backend is included.

## Install from this repository

Clone the complete source; the installer no longer bootstraps the OS or downloads
scripts. On your working iSH installation, reuse `/root/venv/bin/python`:

```sh
git clone https://github.com/braze222/ish-toolkit.git ~/ish-toolkit-v2.1
cd ~/ish-toolkit-v2.1
ISH_PYTHON=/root/venv/bin/python sh install.sh
export PATH="$HOME/.local/bin:$PATH"
hash -r
ish --version
ish selftest --full
```

Use a new clone destination if that folder already exists. Python 3.10+ is
required. For fresh iSH dependencies see [Python setup](docs/python.md). On a
conventional Linux host, create a venv and install `requirements.txt` first.
Keep the source folder in place because launchers refer to it.

## Handbook

- [Download the 24-page PDF](docs/iSH-Toolkit-v2.1-Complete-Guide.pdf)
- [Read the full handbook](BOOKLET.md)
- [Upgrade and recovery instructions](UPGRADE.md)
- [Release notes](RELEASE_NOTES.md)

This repository now contains the 2.1.1-local implementation described by the
handbook. The packaged archive instructions in the book are an alternative to
cloning the repository.

## Upgrade an installed v2 vault

Read UPGRADE.md. Install this source in its own `~/ish-toolkit-v2.1` folder,
then run `ish --version`, `ish selftest --full`, and `ish vault verify`.
Do not reinitialize or migrate an already working v2 vault.
Keep the source folder: launchers refer to it.

## Added in 2.1

- `ish backup export ID --to FILE.ishbackup` verifies and exports a portable bundle.
- `ish backup import FILE.ishbackup` validates safe members, checksums, SQLite
  integrity and vault authentication before adding a new catalogue entry.
- `ish backup recover-vault ID [--preview]` activates a snapshot after explicit
  typed confirmation and password verification, preserving the previous vault.
  Existing vault replacement is one SQLite transaction using the existing lock.
- `ish crypt protect-key` wraps the existing X25519 private key in encrypted
  PKCS8. Identity is unchanged; existing ciphertext remains decryptable. Re-run
  to change the crypt-key password. Minimum new password: 12 characters.
- New file and backup encryption uses streaming CRYPTv2 AES-256-GCM with X25519
  key agreement and HKDF-SHA256. Reads CRYPTv1 up to the old backup limit of
  32 MiB. New streams support up to 60 GiB of plaintext, subject to free disk
  space and practical iSH performance. Working buffers are about 1 MiB each.
- Historical `.bak`, `.before-*`, `.broken-*` and `.pre-release` source copies
  are omitted from this release, without deleting anything from older installs.

## Start here

```sh
ish --help
ish selftest --full
ish db doctor
ish vault verify
ish workspace create notes
ish db tables @notes
ish backup create @notes
ish backup list
```

See BOOKLET.md and the accompanying PDF for a complete guide and worked examples.
Use `ish backup --help`, `ish workspace --help`, `ish db --help` and
`ish vault --help` for exact syntax. Crypt and TOTP print usage with `--help`.

## Important behavior

- Installs do not migrate vaults, protect keys or replace data automatically.
- Ordinary databases remain plaintext; read-only SQL is the default.
- Backup restore/export refuse existing destinations. Import refuses duplicate IDs.
- Recovery replaces vault contents; it does not merge entries. The snapshot's
  master password becomes the active password. The retained previous vault still
  uses its previous password and can be inspected with `--directory`.
- Protected crypt keys require their password for encryption/decryption commands.
  Some backup workflows prompt more than once. The key password and vault password
  are independent. Back up the protected `.crypt/id.key` separately.
- Export bundles contain names, source paths and checksums in an unsigned manifest.
  The payload is encrypted only if the original backup was encrypted. Checksums
  alone do not prove who created an unencrypted snapshot.
- Decryption publishes plaintext only after final authentication. Temporary
  plaintext can exist in private staging while processing. Hard termination may
  leave private staging files; no forensic erasure guarantee is made.
- Recovery and key changes are intended for one local user. Stop legacy clients
  before migration or recovery; they do not respect the new vault lock.

## Development validation

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
python tools/ish.py selftest --full
```

Build-host tests include separate-process interruption recovery, streaming
corruption/truncation rejection, protected keys, legacy ciphertext, portable
bundles, no-clobber behavior and installer/CLI workflows. On-device 2.1 validation
is still required. The previous 2.0 full self-test passed on the user's iSH device.

## Security maintenance

See [the threat model](docs/THREAT_MODEL.md) and
[owner security settings checklist](docs/MAINTAINER_SECURITY.md).
The MIT license previously declared by this repository is now included in
[LICENSE](LICENSE). The 2.1 booklet remains applicable; 2.1.1 adds key-creation
hardening, a Python 3.10 initialization fix and security-maintenance guidance.
