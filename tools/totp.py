#!/usr/bin/env python3
"""TOTP uses the same transactional v2 vault as ordinary secrets."""
import getpass
from pathlib import Path
import sys
import time
import pyotp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.vault_store import VaultStore, VaultError
from tools.vault import command

VDIR = Path.home() / '.vault'


@command
def add(name, secret=None):
    pw = getpass.getpass('Master password: ')
    if secret is None:
        secret = getpass.getpass('Secret (base32): ')
    secret = secret.strip().replace(' ', '').upper()
    try:
        if not secret: raise ValueError()
        pyotp.TOTP(secret).now()
    except Exception as exc:
        raise VaultError('invalid Base32 TOTP secret') from exc
    VaultStore(VDIR).put(name, secret, pw, kind='totp')
    print(f'added: {name}')


@command
def show(name=None):
    values = VaultStore(VDIR).values(getpass.getpass('Master password: '), kind='totp', name=name)
    if not values:
        print('no entries')
        return
    now = int(time.time())
    for entry, secret in values:
        try:
            print(f'{entry:20} {pyotp.TOTP(secret).at(now)}  {30 - now % 30:2}s')
        except Exception as exc:
            raise VaultError('stored TOTP secret is invalid') from exc


@command
def ls():
    names = VaultStore(VDIR).names(kind='totp')
    print('\n'.join(names) if names else '(empty)')


@command
def rm(name):
    VaultStore(VDIR).delete(name, getpass.getpass('Master password: '), kind='totp')
    print(f'deleted: {name}')


def main():
    args = sys.argv[1:]
    if not args: return show()
    if args == ['list']: return ls()
    if len(args) == 2 and args[0] == 'add': return add(args[1])
    if len(args) == 2 and args[0] == 'delete': return rm(args[1])
    if args in (['-h'], ['--help']):
        print('totp add NAME | list | delete NAME | [NAME]')
        return 0
    if len(args) == 1 and args[0] not in {'add', 'delete'} and not args[0].startswith('-'):
        return show(args[0])
    print('Usage: totp add NAME | list | delete NAME | [NAME]; secrets are prompted', file=sys.stderr)
    return 2


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (KeyboardInterrupt, EOFError): raise SystemExit(130)
