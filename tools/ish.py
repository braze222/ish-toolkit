#!/usr/bin/env python3
"""Dispatch local tools with this interpreter and preserve their exit status."""
import subprocess
import sys
from pathlib import Path

COMMANDS = {'compatibility': 'ish-compatibility.py', 'db': 'ish-db.py', 'dbx': 'ish-dbx.py', 'doctor': 'ish-doctor.py', 'vault': 'vault.py',
            'totp': 'totp.py', 'crypt': 'crypt.py', 'shred': 'shred.py',
            'compute': 'ish-compute.py', 'workspace': 'ish-workspace.py',
            'backup': 'ish-backup.py', 'selftest': 'ish-selftest.py'}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
        print('Usage: ish {db|dbx|workspace|backup|vault|totp|crypt|doctor|selftest|compute|shred} [arguments]')
        print('Compatibility: ish compatibility. Compute: status | init | config | cloud | hosts | run | jobs. Run plans by default; see docs/CLOUD_COMPUTE.md.')
        return 0
    if sys.argv[1] == '--version':
        print('ish-toolkit 3.0.2-preview')
        return 0
    if sys.argv[1] in ('status', 'init', 'config', 'cloud', 'hosts', 'run', 'jobs'):
        try:
            return subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'ish-control.py'), *sys.argv[1:]]).returncode
        except KeyboardInterrupt:
            return 130
    script = COMMANDS.get(sys.argv[1])
    if script is None:
        print('ish: unknown command', file=sys.stderr)
        return 2
    if sys.argv[1] not in ('compute', 'compatibility', 'dbx') and not (sys.argv[1] == 'selftest' and '--control' in sys.argv[2:]):
        try:
            import importlib
            for module in ('cryptography', 'argon2', 'pyotp'):
                importlib.import_module(module)
        except (ImportError, OSError):
            print('ish: this command requires the full security dependencies; see docs/COMPATIBILITY.md. Control commands remain available.', file=sys.stderr)
            return 2
    try:
        return subprocess.run([sys.executable, str(Path(__file__).resolve().parent / script), *sys.argv[2:]]).returncode
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
