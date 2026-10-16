#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import workspaces
from lib.storage import StorageError
from lib.db import DBError


def main(argv=None):
    parser = argparse.ArgumentParser(description='Named local SQLite workspaces; refer to one as @NAME.')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('create'); p.add_argument('name'); p.add_argument('--database', help='Register an existing SQLite path instead of creating a database')
    sub.add_parser('list')
    for cmd in ('status', 'path', 'open'):
        sub.add_parser(cmd).add_argument('name')
    args = parser.parse_args(argv)
    try:
        if args.command == 'create': print(json.dumps(workspaces.create(args.name, args.database), indent=2))
        elif args.command == 'list':
            for name in workspaces.names(): print(name)
        elif args.command == 'status':
            info = workspaces.status(args.name)
            print(json.dumps(info, indent=2))
            return 0 if info['integrity'] == 'ok' else 1
        else:
            info = workspaces.load(args.name)
            print(info['directory'])
            if args.command == 'open':
                print(f"Database: {info['database']}")
                print(f"Use: ish db tables @{args.name}")
                print('This prints a location; it does not change your shell directory or active database.')
        return 0
    except (StorageError, DBError) as exc:
        print(f'workspace: {exc}', file=sys.stderr); return 1
    except (OSError, sqlite3.Error):
        print('workspace: storage operation failed', file=sys.stderr); return 1


if __name__ == '__main__': raise SystemExit(main())
