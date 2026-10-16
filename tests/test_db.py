import sqlite3

import pytest

from lib.db import Database, DBError


def test_database_connects(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(db_path)
    db.connect()

    assert db.conn is not None

    db.close()


def test_tables(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(db_path)
    db.connect()

    db.execute_write(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"
    )

    tables = db.tables()

    assert tables == [{"name": "users"}]

    db.close()


def test_parameterized_query(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(db_path)
    db.connect()

    db.execute_write(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"
    )

    db.execute_write(
        "INSERT INTO users (name) VALUES (?)",
        ("alice",),
    )

    rows = db.query(
        "SELECT name FROM users WHERE name = ?",
        ("alice",),
    )

    assert rows == [{"name": "alice"}]

    db.close()


def test_readonly_blocks_write(tmp_path):
    db_path = tmp_path / "test.db"

    writable = Database(db_path)
    writable.connect()

    writable.execute_write(
        "CREATE TABLE users (id INTEGER PRIMARY KEY)"
    )

    writable.close()

    readonly = Database(db_path, readonly=True)
    readonly.connect()

    with pytest.raises(DBError):
        readonly.execute(
            "INSERT INTO users DEFAULT VALUES"
        )

    readonly.close()


def test_integrity_check(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(db_path)
    db.connect()

    assert db.integrity_check() is True

    db.close()
