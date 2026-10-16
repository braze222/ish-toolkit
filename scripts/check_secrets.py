#!/usr/bin/env python3
"""Limited secret-pattern check. Prints locations, never matched values.

Not a replacement for GitHub secret scanning or a full credential audit.
"""
import argparse
from pathlib import Path
import re
import subprocess

PATTERNS = {
    'github-token': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})'),
    'aws-access-key-id': re.compile(rb'(?:AKIA|ASIA)[A-Z0-9]{16}'),
    'openai-project-key': re.compile(rb'sk-proj-[A-Za-z0-9_-]{40,}'),
    'private-key-block': re.compile(rb'^-----BEGIN (?:ENCRYPTED |RSA |EC |OPENSSH )?PRIVATE KEY-----\r?$', re.M),
    'sqlite-database': re.compile(rb'\ASQLite format 3\x00'),
}


def findings(data):
    return [label for label, pattern in PATTERNS.items() if pattern.search(data)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    def git(*command):
        return subprocess.check_output(['git', '-C', str(root), *command])
    failures = []
    checked = 0
    if args.history:
        if git('rev-parse', '--is-shallow-repository').strip() == b'true':
            raise SystemExit('History check requires a full clone; fetch complete history first.')
        objects = git('rev-list', '--objects', '--all').splitlines()
        for entry in objects:
            oid = entry.split(b' ', 1)[0].decode('ascii')
            if git('cat-file', '-t', oid).strip() != b'blob': continue
            checked += 1
            labels = findings(git('cat-file', 'blob', oid))
            if labels: failures.append((oid, labels))
    else:
        for name in git('ls-files', '-z').decode().split('\0'):
            if not name: continue
            path = root/name
            if path.is_symlink(): continue
            checked += 1
            labels = findings(path.read_bytes())
            if labels: failures.append((name, labels))
    for location, labels in failures:
        print('Potential secret/data exposure:', location, ', '.join(labels))
    print(f'Checked {checked} files/blobs; {len(failures)} pattern findings. Coverage is limited.')
    return 1 if failures else 0


if __name__ == '__main__': raise SystemExit(main())
