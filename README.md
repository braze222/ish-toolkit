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
