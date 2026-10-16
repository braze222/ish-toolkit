import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def run(tmp_path):
    env = dict(os.environ, HOME=str(tmp_path))
    def call(*args, input=None):
        return subprocess.run([sys.executable, str(ROOT / 'tools' / 'ish.py'), *map(str, args)],
                              env=env, cwd=tmp_path, text=True, input=input, capture_output=True)
    return call


def test_db_lifecycle(run, tmp_path):
    db = tmp_path / 'source.db'
    assert run('db', 'init', db).returncode == 0
    assert run('db', 'init', db).returncode != 0
    assert run('db', 'query', db, '--sql', 'CREATE TABLE t(x)').returncode != 0
    flags = ('--write', '--allow-destructive')
    assert run('db', 'query', db, '--sql', 'CREATE TABLE t(x)', *flags).returncode == 0
    assert run('db', 'query', db, '--sql', 'INSERT INTO t VALUES (?)', '--params-file', '-',
               *flags, input=json.dumps(['private value'])).returncode == 0
    assert run('db', 'tables', db).stdout.strip() == 't'
    assert json.loads(run('db', 'schema', db, 't').stdout)['name'] == 'x'
    assert json.loads(run('db', 'query', db, '--file', '-', input='SELECT * FROM t').stdout) == {'x': 'private value'}
    backup = tmp_path / 'backup.db'
    restored = tmp_path / 'restored.db'
    assert run('db', 'backup', db, backup).returncode == 0
    assert run('db', 'restore', backup, restored).returncode == 0
    assert run('db', 'restore', backup, db).returncode != 0
    assert run('db', 'query', restored, '--sql', 'SELECT * FROM t').returncode == 0
    log = (tmp_path / '.ish-toolkit/db/audit.jsonl').read_text()
    assert 'private value' not in log and 'INSERT' not in log


def test_exit_codes_and_doctor(run):
    assert run('unknown').returncode == 2
    assert run('db', 'tunnel').returncode == 2
    assert run('db', 'doctor').returncode == 0


def test_missing_source_write_does_not_create(run, tmp_path):
    path = tmp_path / 'missing.db'
    assert run('db', 'query', path, '--sql', 'CREATE TABLE t(x)', '--write', '--allow-destructive').returncode != 0
    assert not path.exists()


def test_corrupt_backup_reports_failure_without_traceback(run, tmp_path):
    source = tmp_path / 'corrupt.db'
    source.write_text('not a sqlite file')
    destination = tmp_path / 'copy.db'
    result = run('db', 'backup', source, destination)
    assert result.returncode != 0
    assert 'Traceback' not in result.stderr
    assert not destination.exists()


def test_audit_failure_prevents_mutation(run, tmp_path):
    directory = tmp_path / '.ish-toolkit/db'
    directory.mkdir(parents=True)
    target = tmp_path / 'untouched'
    target.write_text('private')
    (directory / 'audit.jsonl').symlink_to(target)
    database = tmp_path / 'new.db'
    assert run('db', 'init', database).returncode != 0
    assert not database.exists()
    assert target.read_text() == 'private'
