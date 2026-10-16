#!/usr/bin/env python3
"""Verified local backups. SOURCE is @workspace, SQLite path, or vault."""
import argparse
import getpass
import json
from pathlib import Path
import sqlite3
import tarfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import backups, transfer, recovery
from lib.storage import StorageError
from lib.db import DBError
from lib.vault_store import VaultError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('create'); p.add_argument('source'); p.add_argument('--encrypt', action='store_true')
    sub.add_parser('list')
    sub.add_parser('verify').add_argument('id')
    p = sub.add_parser('restore'); p.add_argument('id'); p.add_argument('--to', required=True); p.add_argument('--preview', action='store_true')
    p = sub.add_parser('export'); p.add_argument('id'); p.add_argument('--to', required=True)
    sub.add_parser('import').add_argument('bundle')
    p = sub.add_parser('recover-vault'); p.add_argument('id')
    p.add_argument('--preview', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'list': result = backups.listing()
        elif args.command == 'create':
            password = getpass.getpass('Vault master password: ') if args.source == 'vault' else None
            result = backups.create(args.source, args.encrypt, password)
        elif args.command == 'import':
            info = transfer.inspect_bundle(Path(args.bundle).expanduser())
            password = getpass.getpass('Snapshot vault password: ') if info['kind'] == 'vault' else None
            result = transfer.import_bundle(args.bundle, password)
        elif args.command == 'recover-vault':
            info = backups.load(args.id)
            if info['kind'] != 'vault': raise StorageError('recovery requires a vault backup')
            plan = {'id': args.id, 'action': 'replace active vault contents after verification; retain previous vault',
                    'snapshot_password_becomes_active': True}
            print(json.dumps(plan, indent=2))
            if args.preview: return 0
            if input('Type RECOVER to activate this snapshot: ') != 'RECOVER':
                raise StorageError('recovery cancelled; active vault unchanged')
            password = getpass.getpass('Snapshot vault password: ')
            current = getpass.getpass('Current active vault password: ') if (Path.home()/'.vault/vault-v2.db').exists() else None
            result = recovery.recover(args.id, password, current)
        else:
            info = backups.load(args.id)
            if args.command == 'restore' and args.preview:
                result = {'id': args.id, 'kind': info['kind'], 'encrypted': info['encrypted'],
                          'to': str(Path(args.to).expanduser().absolute()),
                          'destination_exists': Path(args.to).expanduser().exists(),
                          'action': 'plan only; payload not yet verified; no files restored'}
            else:
                password = getpass.getpass('Password used by this vault snapshot: ') if info['kind'] == 'vault' else None
                if args.command == 'export': result = transfer.export_bundle(args.id, args.to, password)
                elif args.command == 'verify': result = backups.verify(args.id, password)
                else: result = backups.restore(args.id, args.to, password)
        print(json.dumps(result, indent=2))
        return 0
    except (StorageError, DBError, VaultError) as exc:
        print(f'backup: {exc}', file=sys.stderr); return 1
    except (OSError, sqlite3.Error, ValueError, tarfile.TarError):
        print('backup: storage operation failed; check paths, permissions and available space', file=sys.stderr); return 1


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (KeyboardInterrupt, EOFError): raise SystemExit(130)
