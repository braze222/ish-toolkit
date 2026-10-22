#!/usr/bin/env python3
"""DBX-inspired local database explorer for iSH Toolkit; SQLite-only and read-only by default."""
import argparse
import csv
import json
import sqlite3
import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.db import SQLiteDB, DBError
from lib.db_policy import DBPolicy
from lib.workspaces import resolve_database
from lib.storage import StorageError


def parser():
    p = argparse.ArgumentParser(
        prog="ish dbx",
        description="Explore local SQLite databases with bounded, read-only-by-default queries.",
    )
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities", help="Show implemented and unavailable capabilities")
    for name in ("tables", "views", "indexes"):
        cmd = sub.add_parser(name, help=f"List database {name}")
        cmd.add_argument("database")
        cmd.add_argument("--format", choices=("text", "json"), default="text")
    schema = sub.add_parser("schema", help="Describe a table, including indexes and foreign keys")
    schema.add_argument("database")
    schema.add_argument("table")
    schema.add_argument("--format", choices=("text", "json"), default="text")
    query = sub.add_parser("query", help="Run one SQL statement (read-only by default)")
    query.add_argument("database")
    source = query.add_mutually_exclusive_group(required=True)
    source.add_argument("--sql", help="SQL text (avoid secrets in shell history)")
    source.add_argument("--file", help="SQL file path, or - for stdin")
    query.add_argument("--params-file", help="JSON array/object of bound parameters")
    query.add_argument("--format", choices=("jsonl", "csv"), default="jsonl")
    query.add_argument("--limit", type=int, default=1000, help="Maximum rows emitted (default: 1000)")
    query.add_argument("--timeout", type=float, default=5.0, help="Query deadline in seconds (default: 5)")
    query.add_argument("--write", action="store_true", help="Permit non-destructive writes")
    query.add_argument("--allow-destructive", action="store_true", help="Also permit destructive SQL; requires --write")
    sub.add_parser("doctor", help="Run safe database-policy and capability checks")
    return p


def read_text(path):
    return sys.stdin.read() if path == "-" else Path(path).expanduser().read_text(encoding="utf-8")


def emit_rows(rows, output_format):
    if output_format == "json":
        print(json.dumps(rows, default=lambda v: {"hex": v.hex()}))
    else:
        for row in rows:
            print(json.dumps(row, default=lambda v: {"hex": v.hex()}, sort_keys=True))


def list_objects(db, kind):
    if kind == "tables":
        sql = "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    elif kind == "views":
        sql = "SELECT name FROM sqlite_schema WHERE type='view' ORDER BY name"
    else:
        sql = "SELECT name, tbl_name AS table_name, sql FROM sqlite_schema WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    return db.query(sql)


def describe(db, table):
    # Table names are passed as bound values to SQLite's table-valued PRAGMA functions.
    return {
        "table": table,
        'columns': db.query('SELECT cid, name, type, "notnull" AS "notnull", dflt_value, pk FROM pragma_table_info(?)', (table,)),
        'indexes': db.query('SELECT name, "unique" AS is_unique, origin, partial FROM pragma_index_list(?)', (table,)),
        'foreign_keys': db.query('SELECT id, seq, "table" AS referenced_table, "from" AS source_column, "to" AS target_column, on_update, on_delete FROM pragma_foreign_key_list(?)', (table,)),
    }


def capabilities():
    data = {
        "product": "iSH Toolkit DBX-inspired database explorer",
        "implemented": ["local SQLite", "read-only-by-default SQL", "parameter binding", "query row limits", "query deadlines", "JSONL/CSV output", "table/view/index inspection", "schema and foreign-key inspection", "workspace references"],
        "optional_or_future": ["PostgreSQL driver", "MySQL/MariaDB driver", "DBX CLI bridge", "MCP client/server", "remote connection profiles"],
        "platform_notes": ["Uses Python standard library plus existing iSH Toolkit modules.", "No Node.js, Rust, Docker daemon, or network access is required.", "This is not the upstream DBX desktop application."],
    }
    print(json.dumps(data, indent=2, sort_keys=True))


def doctor():
    with tempfile.TemporaryDirectory(prefix="ish-dbx-doctor-") as temp:
        path = Path(temp) / "probe.db"
        with SQLiteDB(path, DBPolicy(read_only=False, allow_destructive=True)) as db:
            db.execute("CREATE TABLE sample(value TEXT)")
        with SQLiteDB(path, DBPolicy()) as db:
            if db.query("SELECT 1 AS ok") != [{"ok": 1}]:
                raise DBError("SQLite probe failed")
            try:
                db.execute("CREATE TABLE should_be_blocked(value TEXT)")
            except DBError:
                pass
            else:
                raise DBError("read-only policy probe failed")
    print("PASS: SQLite available; default policy blocks writes.")
    print("SCOPE: local SQLite only; remote drivers and upstream DBX bridge are not implemented.")


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if args.command == "capabilities":
        capabilities()
        return 0
    if args.command == "doctor":
        doctor()
        return 0
    if args.command == "query":
        if args.limit < 1 or args.limit > 100000:
            p.error("--limit must be between 1 and 100000")
        if args.timeout <= 0 or args.timeout > 300:
            p.error("--timeout must be greater than 0 and at most 300 seconds")
        if args.write != args.allow_destructive:
            p.error("writes require both --write and --allow-destructive")
        if args.file == "-" and args.params_file == "-":
            p.error("SQL and parameters cannot both consume stdin")
    try:
        path = resolve_database(args.database)
        if not Path(path).is_file():
            raise DBError("database does not exist; initialize it with 'ish db init' first")
        policy = (DBPolicy(read_only=not args.write, allow_destructive=args.allow_destructive)
                  if args.command == "query" else DBPolicy())
        with SQLiteDB(path, policy) as db:
            if args.command in ("tables", "views", "indexes"):
                rows = list_objects(db, args.command)
                if args.format == "json":
                    print(json.dumps(rows, indent=2))
                else:
                    for row in rows:
                        print(row.get("name", ""))
            elif args.command == "schema":
                result = describe(db, args.table)
                if args.format == "json":
                    print(json.dumps(result, indent=2))
                else:
                    for section in ("columns", "indexes", "foreign_keys"):
                        print(f"[{section}]")
                        for row in result[section]:
                            print(json.dumps(row, sort_keys=True))
            elif args.command == "query":
                sql = args.sql if args.sql is not None else read_text(args.file)
                params = json.loads(read_text(args.params_file)) if args.params_file else []
                if not isinstance(params, (list, dict)):
                    raise ValueError("parameters must be a JSON array or object")
                started = time.monotonic()
                def progress():
                    return 1 if time.monotonic() - started > args.timeout else 0
                db.connect()
                db.conn.set_progress_handler(progress, 1000)
                cursor = db.execute(sql, params)
                if not cursor.description:
                    if args.write:
                        db.conn.commit()
                    print(json.dumps({"rows_changed": cursor.rowcount}))
                    return 0
                fields = [column[0] for column in cursor.description]
                if args.format == "csv":
                    writer = csv.writer(sys.stdout, lineterminator="\n")
                    writer.writerow(fields)
                    count = 0
                    for row in cursor:
                        if count >= args.limit:
                            break
                        writer.writerow([value.hex() if isinstance(value, bytes) else value for value in row])
                        count += 1
                else:
                    count = 0
                    for row in cursor:
                        if count >= args.limit:
                            break
                        print(json.dumps(dict(row), default=lambda v: {"hex": v.hex()}, sort_keys=True))
                        count += 1
                if args.write:
                    db.conn.commit()
            return 0
    except (DBError, StorageError, sqlite3.Error, OSError, ValueError, TypeError) as exc:
        print(f"ish dbx: operation failed ({type(exc).__name__}); check inputs, permissions and policy flags", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
