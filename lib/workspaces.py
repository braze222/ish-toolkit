"""Explicit named local SQLite workspaces. No credentials or implicit active DB."""
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
from .storage import StorageError, private_dir, lock, read_json, write_json_new, sync_dir
from .db import SQLiteDB, DBError

NAME = re.compile(r'[a-z][a-z0-9_-]{0,47}\Z')


def state_root():
    return private_dir(Path.home() / '.ish-toolkit')


def workspace_root():
    return private_dir(state_root() / 'workspaces')


def validate_name(name):
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise StorageError('name must start with a lowercase letter and contain up to 48 letters, digits, _ or -')
    return name


def public_database(path):
    path = Path(path).expanduser().resolve()
    if path.is_relative_to((Path.home() / '.vault').resolve()):
        raise StorageError('vault storage is not an ordinary workspace database')
    return path


def load(name):
    validate_name(name)
    directory = workspace_root() / name
    if directory.is_symlink():
        raise StorageError('workspace directory cannot be a symlink')
    info = read_json(directory / 'workspace.json')
    if info.get('version') != 1 or info.get('name') != name or not isinstance(info.get('database'), str):
        raise StorageError('invalid workspace configuration')
    if not Path(info['database']).is_absolute():
        raise StorageError('workspace database must be an absolute path')
    info['database'] = str(public_database(info['database']))
    info['directory'] = str(directory)
    return info


def resolve_database(value):
    if str(value).startswith('@'):
        return Path(load(str(value)[1:])['database'])
    return public_database(value)


def create(name, database=None):
    validate_name(name)
    root = workspace_root()
    destination = root / name
    with lock(root / '.workspaces.lock'):
        if destination.exists() or destination.is_symlink():
            raise StorageError('workspace already exists')
        if database is not None:
            database = public_database(database)
            with SQLiteDB(database) as db:
                if not db.integrity_check(): raise DBError('database integrity check failed')
        stage = Path(tempfile.mkdtemp(prefix='.workspace-', dir=root))
        try:
            if database is None:
                fd = os.open(stage / 'data.db', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                conn = sqlite3.connect(stage / 'data.db')
                try:
                    conn.execute('PRAGMA user_version=0')
                finally:
                    conn.close()
                database = destination / 'data.db'
            for sub in ('queries', 'reports'):
                (stage / sub).mkdir(mode=0o700)
            write_json_new(stage / 'workspace.json', {'version': 1, 'name': name, 'database': str(database)})
            sync_dir(stage)
            os.rename(stage, destination)
            sync_dir(root)
        finally:
            if stage.exists(): shutil.rmtree(stage)
    return load(name)


def names():
    return sorted(p.name for p in workspace_root().iterdir() if NAME.fullmatch(p.name) and p.is_dir())


def status(name):
    info = load(name)
    with SQLiteDB(info['database']) as db:
        info['integrity'] = 'ok' if db.integrity_check() else 'failed'
        info['tables'] = [row['name'] for row in db.tables()]
    return info
