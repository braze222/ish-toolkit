import os
import sqlite3
import pytest
from lib.db import SQLiteDB, DBError
from lib.db_policy import DBPolicy, validate_sql

WRITE = DBPolicy(False, True)


@pytest.fixture
def dbpath(tmp_path):
    path = tmp_path / 'odd ?# name.db'
    with SQLiteDB(path, WRITE) as db:
        db.execute('CREATE TABLE items(value TEXT)')
        db.execute('INSERT INTO items VALUES (?)', ('original',))
    return path


@pytest.mark.parametrize('sql', [
    'CREATE TABLE extra(x)', 'WITH x AS (SELECT 1) DELETE FROM items',
    'PRAGMA writable_schema=ON', "ATTACH ':memory:' AS extra",
    'PRAGMA query_only=OFF', "SELECT load_extension('anything')",
    "SELECT * FROM pragma_query_only(0)",
])
def test_readonly_policy(dbpath, sql):
    with SQLiteDB(dbpath) as db:
        with pytest.raises(DBError):
            db.execute(sql)
        assert db.query('SELECT value FROM items') == [{'value': 'original'}]


def test_authorizer_direct_bypass(dbpath):
    with SQLiteDB(dbpath) as db:
        with pytest.raises(sqlite3.DatabaseError):
            db.conn.execute('CREATE TEMP TABLE bypass(x)')
        with pytest.raises(sqlite3.DatabaseError):
            db.conn.execute('PRAGMA query_only=OFF')


def test_quoted_keywords_and_semicolon(dbpath):
    sql = "SELECT 'delete; insert' AS value; -- safe trailing comment"
    validate_sql(sql, DBPolicy())
    with SQLiteDB(dbpath) as db:
        assert db.query(sql) == [{'value': 'delete; insert'}]


def test_default_missing_file(tmp_path):
    path = tmp_path / 'missing.db'
    with pytest.raises(DBError):
        SQLiteDB(path).connect()
    assert not path.exists()


def test_schema_bound_identifier(dbpath):
    with SQLiteDB(dbpath) as db:
        assert db.schema('items')[0]['name'] == 'value'
        assert db.schema("items'); DROP TABLE items;--") == []


def test_transaction_rollback(dbpath):
    with pytest.raises(RuntimeError):
        with SQLiteDB(dbpath, WRITE) as db:
            db.execute('DELETE FROM items')
            raise RuntimeError()
    assert db.conn is None
    with SQLiteDB(dbpath) as db:
        assert len(db.query('SELECT * FROM items')) == 1


def test_backup_wal_and_no_clobber(dbpath, tmp_path):
    external = sqlite3.connect(dbpath)
    external.execute('PRAGMA journal_mode=WAL')
    external.execute('INSERT INTO items VALUES (?)', ('from WAL',))
    external.commit()
    destination = tmp_path / 'snapshot.db'
    try:
        with SQLiteDB(dbpath) as db:
            db.backup(destination)
            with pytest.raises(FileExistsError):
                db.backup(destination)
        with SQLiteDB(destination) as db:
            assert len(db.query('SELECT * FROM items')) == 2
            assert db.integrity_check()
        assert destination.stat().st_mode & 0o777 == 0o600
    finally:
        external.close()


def test_new_file_permissions(tmp_path):
    with SQLiteDB(tmp_path / 'new.db', WRITE) as db:
        assert db.path.stat().st_mode & 0o777 == 0o600
