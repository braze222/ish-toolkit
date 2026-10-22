# iSH Toolkit 3.0.2-preview

**Early release, not independently security-audited.** Start with the
[Safe learning guide](docs/SAFE_START.md), use dummy data, and keep independent
recovery copies. Read [SECURITY.md](SECURITY.md) before storing important secrets.

[![Toolkit tests](https://github.com/braze222/ish-toolkit/actions/workflows/python-package.yml/badge.svg)](https://github.com/braze222/ish-toolkit/actions/workflows/python-package.yml)
[![Security baseline](https://github.com/braze222/ish-toolkit/actions/workflows/security.yml/badge.svg)](https://github.com/braze222/ish-toolkit/actions/workflows/security.yml)

An iSH/Alpine control terminal for offline security tools and explicitly authorized
compute. Preserve encrypted secrets/TOTP, SQLite workspaces and portable backups;
run reviewed commands locally or over verified SSH, and dispatch the bundled
GitHub Actions workflow. Google Cloud Shell is the primary **interactive** console
integration, with AWS and Azure discovery/setup alongside it. No resource
provisioning, cloud subscription, background daemon or quota bypass is required.

Read the [new compute guide](docs/CLOUD_COMPUTE.md) and
[validation record](docs/COMPUTE_VALIDATION.md) and [release readiness](docs/RELEASE_READINESS.md) before remote use. This is a preview: the
new runtime has not yet been verified on your iPhone or live cloud-console accounts.

## Older iPhones and mixed devices

Use the [compatibility guide](docs/COMPATIBILITY.md). We target runtime capabilities,
not a guessed iPhone generation. New: dependency-light `--profile control`, a
no-Python shell report, `ish compatibility`, `ish selftest --control`, and portable
select-based job I/O. No claim of every-generation testing is made.

## Install from this repository

Clone the complete source; the installer no longer bootstraps the OS or downloads
scripts. On your working iSH installation, reuse `/root/venv/bin/python`:

```sh
git clone https://github.com/braze222/ish-toolkit.git ~/ish-toolkit-v3-preview
cd ~/ish-toolkit-v3-preview
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

The 2.1 handbook/PDF covers the preserved offline security tools. Its version and
archive names are historical; the 3.0 compute commands are documented separately
in [CLOUD_COMPUTE.md](docs/CLOUD_COMPUTE.md). Do not treat the old PDF as documentation
of the new remote-execution boundary.

## Upgrade an installed v2 vault

Read UPGRADE.md. Install this source in its own `~/ish-toolkit-v3-preview` folder,
then run `ish --version`, `ish selftest --full`, and `ish vault verify`.
Do not reinitialize or migrate an already working v2 vault.
Keep the source folder: launchers refer to it.

## New compute quick start

```sh
ish init
ish status
ish compute providers
ish cloud google open
ish run --spec examples/jobs/local.json
ish run --spec examples/jobs/local.json --execute
ish jobs list
```

`run` plans by default. Remote work additionally needs `--allow-remote`; secret
delivery needs `--allow-secrets`; unknown-cost targets need `--allow-cost`.
These permissions cannot be granted by a downloaded job file. Read the exact
command before executing it: an ordinary command runs with your account rights.

The modular control plane separates schema/private state, provider transports,
endpoint execution, scheduling and CLI. SSH requires independently verified
host keys; logs are bounded and sanitized before saving; artifact paths and
archives are constrained; connection loss never triggers automatic resubmission.
See the guide for [host registration](docs/CLOUD_COMPUTE.md#connect-an-existing-linux-host),
[Actions authentication](docs/CLOUD_COMPUTE.md#github-actions-setup),
[secrets](docs/CLOUD_COMPUTE.md#secrets-and-log-safety) and
[recovery/uninstall](docs/CLOUD_COMPUTE.md#operations-recovery-and-uninstall).

## Preserved from 2.1

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
bundles, no-clobber behavior and installer/CLI workflows. On-device validation of the new runtime
is still required. The previous 2.0 full self-test passed on the user's iSH device.

## Security maintenance

See [the threat model](docs/THREAT_MODEL.md) and
[owner security settings checklist](docs/MAINTAINER_SECURITY.md).
The MIT license previously declared by this repository is now included in
[LICENSE](LICENSE). The 2.1 booklet remains applicable; 2.1.1 adds key-creation
hardening, a Python 3.10 initialization fix and security-maintenance guidance.

## Elmatrix: independent research preview

Use `sh install-elmatrix.sh` to install the separate `elmatrix` command without
changing `ish`. Research service niches, children's-content topics or custom
queries with `scan`, inspect timestamped observations with `trends`, create a
`report`, and check `providers`. No video generation, inferred competitor revenue
or paid AI fallback. Main-branch CI automatically builds and verifies a standalone
deployment bundle. See [Elmatrix setup, OpenCode handoff and limits](docs/ELMATRIX.md).

## Elmatrix standalone prototype (separate package)

The experimental standalone research prototype is isolated in
[`elmatrix-standalone/`](elmatrix-standalone/README.md), with its own Python
package, CLI, local database, dashboard, tests, and CI workflow. It does not
import toolkit modules, register an `ish` subcommand, or change the toolkit
installer or security/compute state. This folder placement is for versioned
review inside this repository; it can be extracted into its own GitHub repository
when repository creation is available. Its 0.3 preview adds explicit RSS/Atom
collection and source provenance; it does not yet claim verified market demand or
fully automated competitive intelligence.
