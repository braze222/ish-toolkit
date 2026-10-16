#!/usr/bin/env python3
"""Small local SQLite CLI for iSH."""
import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.db import SQLiteDB, DBError
from lib.db_policy import DBPolicy
from lib.db_audit import AuditLog
from lib.workspaces import resolve_database
from lib.storage import StorageError


def build_parser():
    parser = argparse.ArgumentParser(prog='ish-db', description='Local SQLite tools. Read-only by default.')
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='Create a new private SQLite file (never overwrite)')
    init.add_argument('database')
    query = sub.add_parser('query', help='Execute one SQL statement')
    query.add_argument('database')
    source = query.add_mutually_exclusive_group(required=True)
    source.add_argument('--sql', help='SQL text; avoid putting sensitive literals in shell history')
    source.add_argument('--file', help='Read SQL from file, or - for stdin')
    query.add_argument('--params-file', help='JSON array/object of bound values; - for stdin')
    query.add_argument('--write', action='store_true')
    query.add_argument('--allow-destructive', action='store_true')
    for name in ('tables', 'schema'):
        p = sub.add_parser(name)
        p.add_argument('database')
        if name == 'schema':
            p.add_argument('table')
    for name in ('backup', 'restore'):
        p = sub.add_parser(name, help='Copy a consistent snapshot to a NEW destination')
        p.add_argument('database', help='Source database')
        p.add_argument('destination', help='New destination; existing files are refused')
    sub.add_parser('doctor', help='Exercise read-only policy, rollback, and backup on temporary data')
    return parser


def read_input(path):
    return sys.stdin.read() if path == '-' else Path(path).expanduser().read_text(encoding='utf-8')


def doctor():
    with tempfile.TemporaryDirectory(prefix='ish-db-check-') as temp:
        path = Path(temp) / 'test.db'
        writable = DBPolicy(False, True)
        with SQLiteDB(path, writable) as db:
            db.execute('CREATE TABLE sample(value TEXT)')
            db.execute('INSERT INTO sample VALUES (?)', ('ok',))
        with SQLiteDB(path) as db:
            if db.query('SELECT value FROM sample') != [{'value': 'ok'}]:
                raise DBError('read test failed')
            for sql in ('DELETE FROM sample', 'PRAGMA writable_schema=ON',
                        "ATTACH DATABASE ':memory:' AS extra", 'SELECT 1; SELECT 2'):
                try:
                    db.execute(sql)
                except DBError:
                    pass
                else:
                    raise DBError('policy test failed')
            db.backup(Path(temp) / 'copy.db')
        try:
            with SQLiteDB(path, writable) as db:
                db.execute('INSERT INTO sample VALUES (?)', ('rollback',))
                raise ValueError('rollback test')
        except ValueError:
            pass
        with SQLiteDB(path) as db:
            if db.query('SELECT count(*) AS n FROM sample') != [{'n': 1}]:
                raise DBError('rollback test failed')
        with SQLiteDB(Path(temp) / 'copy.db') as db:
            if not db.integrity_check():
                raise DBError('snapshot test failed')
    print('PASS: read-only policy, parameter binding, rollback, backup integrity')
    print('Scope: local SQLite only; no remote connectors or credential adapter.')


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == 'query':
        if args.write != args.allow_destructive:
            parser.error('writes require both --write and --allow-destructive')
        if args.file == '-' and args.params_file == '-':
            parser.error('SQL and parameters cannot both consume stdin')
    audit = None
    try:
        if hasattr(args, 'database'):
            if args.command == 'init' and args.database.startswith('@'):
                raise StorageError('use ish workspace create NAME to initialize a workspace')
            args.database = str(resolve_database(args.database))
        audit = AuditLog(Path.home() / '.ish-toolkit' / 'db' / 'audit.jsonl')
        # Probe logging before any database mutation; every attempt starts as incomplete.
        audit.record(args.command, success=False)
        if args.command == 'doctor':
            doctor()
        elif args.command == 'init':
            path = Path(args.database).expanduser()
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            # Fixed initialization statement on the exclusively created empty file.
            # set_authorizer(None) is not supported on Python 3.10. Normal query
            # connections continue to enforce their authorizer unchanged.
            connection = sqlite3.connect(path)
            try:
                connection.execute('PRAGMA user_version=0')
                connection.commit()
            finally:
                connection.close()
            print('Database initialized')
        else:
            policy = DBPolicy(False, True) if args.command == 'query' and args.write else DBPolicy()
            # Queries never create a missing file, even in write mode.
            if not Path(args.database).expanduser().is_file():
                raise DBError('source database does not exist; use init first')
            with SQLiteDB(args.database, policy) as db:
                if args.command == 'query':
                    sql = args.sql if args.sql is not None else read_input(args.file)
                    params = json.loads(read_input(args.params_file)) if args.params_file else []
                    if not isinstance(params, (list, dict)):
                        raise ValueError('parameters must be a JSON array or object')
                    cursor = db.execute(sql, params)
                    # Stream results; large result sets need not fit in iSH memory.
                    if cursor.description:
                        for row in cursor:
                            print(json.dumps(dict(row), default=lambda value: {'hex': value.hex()}))
                    else:
                        print(json.dumps({'rows_changed': cursor.rowcount}))
                elif args.command == 'tables':
                    for row in db.tables():
                        print(row['name'])
                elif args.command == 'schema':
                    for row in db.schema(args.table):
                        print(json.dumps(row))
                else:
                    db.backup(args.destination)
                    print('Snapshot copied to new destination')
        audit.record(args.command, success=True)
        return 0
    except (DBError, StorageError, sqlite3.Error, OSError, ValueError, TypeError) as exc:
        # Do not print SQL, parameters, filesystem paths, or SQLite error literals.
        print(f'ish-db: operation failed ({type(exc).__name__}); check inputs, permissions and write flags', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
