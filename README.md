# ish-toolkit

Bootstrap iSH (Alpine Linux on iOS) for real development.

## Problems solved

- Frozen Alpine repos from 2023
- pip install cryptography fails (Rust toolchain missing for i386-musl)
- PEP 668 externally-managed-environment errors
- Node.js 20.15+ crashes with SIGILL on iSH

## Install

    curl -fsSL https://raw.githubusercontent.com/braze222/ish-toolkit/main/install.sh | sh

Then:

    bash
    source /root/venv/bin/activate

## What you get

- Python 3.12 with cryptography, argon2-cffi, pyotp
- Build toolchain (gcc, cmake, make)
- Git, SSH, curl, wget
- Four security tools:
  - vault - encrypted secrets manager
  - totp  - offline 2FA codes
  - crypt - file encryption (X25519 + ChaCha20-Poly1305)
  - shred - secure file deletion

## License

MIT

## Toolkit v2.1 handbook

- [Download the complete PDF guide](docs/iSH-Toolkit-v2.1-Complete-Guide.pdf)
- [Read the guide on GitHub](docs/BOOKLET-v2.1.md)

The handbook documents the separately packaged **2.1.0-local** release. This documentation update does not upgrade the older toolkit code in this repository. Follow the handbook's version-specific installation instructions; existing v2 vaults do not need reinitialization or migration.
