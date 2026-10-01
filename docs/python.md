# Python on iSH

## Problem

pip install cryptography fails with:

    Target triple not supported by rustup: i686-unknown-linux-musl

Cause: pip tries to compile from source, and Rust can't target iSH's architecture.

## Fix

Install the pre-built Alpine packages first:

    apk add py3-cryptography py3-argon2-cffi py3-otp

Then create the venv with --system-site-packages:

    python3 -m virtualenv --system-site-packages /root/venv
    source /root/venv/bin/activate

## Rule

For packages needing C/Rust compilation:
1. apk search py3-<name>  - if found, use apk
2. pip install only for pure-Python packages

## PEP 668

Never use --break-system-packages. Always use a venv.
