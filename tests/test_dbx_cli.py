import json
import sqlite3
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "ish-dbx.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        text=True, capture_output=True, timeout=10,
    )


def make_db(path):
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE VIEW active_users AS SELECT id, name FROM users;
        CREATE INDEX idx_users_name ON users(name);
        INSERT INTO users(name) VALUES ('Ada'), ('Grace');
    """)
    conn.commit()
    conn.close()


def test_capabilities_is_explicit_about_scope():
    result = run_cli("capabilities")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "local SQLite" in data["implemented"]
    assert "PostgreSQL driver" in data["optional_or_future"]


def test_tables_and_schema(tmp_path):
    path = tmp_path / "sample.db"
    make_db(path)
    tables = run_cli("tables", path)
    assert tables.returncode == 0
    assert "users" in tables.stdout
    schema = run_cli("schema", path, "users", "--format", "json")
    assert schema.returncode == 0
    data = json.loads(schema.stdout)
    assert data["columns"][1]["name"] == "name"
    assert data["indexes"][0]["name"] == "idx_users_name"


def test_query_is_read_only_and_parameterized(tmp_path):
    path = tmp_path / "sample.db"
    make_db(path)
    result = run_cli("query", path, "--sql", "SELECT name FROM users WHERE name = ?", "--params-file", str(_params_file(tmp_path)), "--format", "jsonl")
    assert result.returncode == 0
    assert json.loads(result.stdout.strip()) == {"name": "Ada"}
    denied = run_cli("query", path, "--sql", "DELETE FROM users")
    assert denied.returncode != 0
    check = sqlite3.connect(path).execute("SELECT count(*) FROM users").fetchone()[0]
    assert check == 2


def _params_file(tmp_path):
    path = tmp_path / "params.json"
    path.write_text('["Ada"]', encoding="utf-8")
    return path


def test_write_requires_both_flags(tmp_path):
    path = tmp_path / "sample.db"
    make_db(path)
    denied = run_cli("query", path, "--sql", "DELETE FROM users WHERE name='Ada'", "--write")
    assert denied.returncode == 2
    allowed = run_cli("query", path, "--sql", "DELETE FROM users WHERE name='Ada'", "--write", "--allow-destructive")
    assert allowed.returncode == 0
    assert json.loads(allowed.stdout)["rows_changed"] == 1


def test_limit_and_csv(tmp_path):
    path = tmp_path / "sample.db"
    make_db(path)
    result = run_cli("query", path, "--sql", "SELECT name FROM users ORDER BY id", "--limit", "1", "--format", "csv")
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["name", "Ada"]


def test_doctor(tmp_path):
    result = run_cli("doctor")
    assert result.returncode == 0, result.stderr
    assert "PASS:" in result.stdout
