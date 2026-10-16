#!/usr/bin/env python3
"""Interactive v2 vault commands. Passwords are never CLI arguments."""
import argparse
from functools import wraps
import getpass
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.vault_store import VaultStore, VaultError, derive
from lib.storage import StorageError

VDIR = Path.home() / '.vault'


def command(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (VaultError, StorageError) as exc:
            print(f'vault: {exc}', file=sys.stderr)
            raise SystemExit(1)
        except (sqlite3.Error, OSError, UnicodeError):
            print('vault: storage operation failed; preserve the files and inspect permissions/integrity', file=sys.stderr)
            raise SystemExit(1)
    return wrapped


def password(prompt='Master password: '):
    return getpass.getpass(prompt)


@command
def init():
    first = password()
    if first != password('Confirm: '):
        raise VaultError('password confirmation does not match')
    VaultStore(VDIR).initialize(first)
    print('vault v2 initialized')


@command
def migrate():
    counts = VaultStore(VDIR).migrate(password('Current legacy master password: '))
    print('Migration verified. v2 is now active; original legacy files were retained.')
    print(json.dumps(counts, sort_keys=True))
    print('Use only the v2 vault/TOTP commands from now on; old clients use the old copy.')


@command
def set_s(name):
    pw = password()
    value = getpass.getpass(f'Value for {name}: ')
    VaultStore(VDIR).put(name, value, pw)
    print(f'stored: {name}')


@command
def get_s(name):
    print(VaultStore(VDIR).get(name, password()))


@command
def ls():
    names = VaultStore(VDIR).names()
    print('\n'.join(names) if names else '(empty)')


@command
def rm(name):
    VaultStore(VDIR).delete(name, password())
    print(f'deleted: {name}')


@command
def passwd():
    old = password('Current master password: ')
    new = password('New master password: ')
    if new != password('Confirm new password: '):
        raise VaultError('password confirmation does not match')
    VaultStore(VDIR).rotate(old, new)
    print('Master password changed in one SQLite transaction.')


@command
def check():
    print(json.dumps(VaultStore(VDIR).check(), sort_keys=True))
    print('Structure checked. Use ish vault verify to authenticate every record.')
    return 0


@command
def verify():
    print(json.dumps(VaultStore(VDIR).check(password()), sort_keys=True))
    print('PASS: password and every encrypted record verified')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, help='Use a separate vault directory, for example a restored copy')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'migrate', 'list', 'passwd', 'check', 'verify'):
        sub.add_parser(name)
    for name in ('set', 'get', 'delete'):
        sub.add_parser(name).add_argument('name')
    args = parser.parse_args(argv)
    if args.directory is not None:
        global VDIR
        VDIR = args.directory.expanduser().absolute()
    if args.command == 'set': return set_s(args.name)
    if args.command == 'get': return get_s(args.name)
    if args.command == 'delete': return rm(args.name)
    return {'init': init, 'migrate': migrate, 'list': ls, 'passwd': passwd,
            'check': check, 'verify': verify}[args.command]()


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (KeyboardInterrupt, EOFError): raise SystemExit(130)
