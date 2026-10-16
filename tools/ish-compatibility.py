#!/usr/bin/env python3
"""Read-only package/runtime report; no secret/config contents or hardware IDs."""
import argparse
import importlib.util
import json
import platform
from pathlib import Path
import struct
import sys


def report():
    dependencies = {name: importlib.util.find_spec(name) is not None
                    for name in ('sqlite3', 'fcntl', 'cryptography', 'argon2', 'pyotp')}
    alpine = Path('/etc/alpine-release')
    return {'python': platform.python_version(), 'python_minimum_met': sys.version_info >= (3,10),
            'pointer_bits': struct.calcsize('P')*8, 'kernel': platform.release(),
            'architecture': platform.machine(), 'alpine': alpine.read_text().strip() if alpine.is_file() else None,
            'ios_version': 'not detectable reliably; supply manually', 'iphone_model': 'supply manually',
            'dependencies_discoverable': dependencies, 'imports_and_crypto_verified': False,
            'io_backend': 'select (no epoll/kqueue required)',
            'profiles': {'control': 'Python 3.10+, POSIX/fcntl; crypto packages optional',
                         'full': 'also needs working cryptography, argon2-cffi and pyotp'},
            'next_step': 'Run install.sh --profile control or full, then the matching self-test. Package presence is not an import test.'}


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(report(), indent=2))
    return 0 if sys.version_info >= (3,10) else 2

if __name__ == '__main__':
    raise SystemExit(main())
