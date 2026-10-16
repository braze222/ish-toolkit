#!/usr/bin/env python3
"""Dispatch local tools with this interpreter and preserve their exit status."""
import subprocess
import sys
from pathlib import Path

COMMANDS = {'db': 'ish-db.py', 'doctor': 'ish-doctor.py', 'vault': 'vault.py',
            'totp': 'totp.py', 'crypt': 'crypt.py', 'shred': 'shred.py',
            'compute': 'ish-compute.py', 'workspace': 'ish-workspace.py',
            'backup': 'ish-backup.py', 'selftest': 'ish-selftest.py'}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print('Usage: ish {db|workspace|backup|vault|totp|crypt|doctor|selftest|compute|shred} [arguments]')
        print('Core: offline security utilities and local SQLite. Compute: existing status checks only.')
        return 0
    if sys.argv[1] == '--version':
        print('ish-toolkit 2.1.0-local')
        return 0
    script = COMMANDS.get(sys.argv[1])
    if script is None:
        print('ish: unknown command', file=sys.stderr)
        return 2
    try:
        return subprocess.run([sys.executable, str(Path(__file__).resolve().parent / script), *sys.argv[2:]]).returncode
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
