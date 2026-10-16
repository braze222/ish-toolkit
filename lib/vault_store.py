"""Version 2 vault: metadata and ciphertext change in one SQLite transaction.

Legacy files are never edited by migration. New clients refuse legacy writes.
Locks coordinate these clients; callers must stop older clients during migration.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import tempfile
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import hash_secret_raw, Type
from .storage import private_dir, regular_file, lock, sync_dir, sync_file

VERSION = 2
KDF = 'argon2id:t3:m65536:p1:len32'


class VaultError(Exception):
    pass


def derive(password, salt):
    return hash_secret_raw(secret=password.encode(), salt=salt, time_cost=3,
                           memory_cost=65536, parallelism=1, hash_len=32, type=Type.ID)


def encrypt(key, value, associated=None):
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, value, associated)


def decrypt(key, blob, associated=None):
    try:
        return AESGCM(key).decrypt(blob[:12], blob[12:], associated)
    except (InvalidTag, ValueError, TypeError) as exc:
        raise VaultError('wrong password or damaged vault record') from exc


def _checkpoint(stage):
    """Private fault-injection seam used by tests; no environment-driven behavior."""


def _connect(path, writable=False):
    regular_file(path)
    conn = sqlite3.connect(Path(path).resolve().as_uri() + ('?mode=rw' if writable else '?mode=ro'),
                           uri=True, isolation_level=None, timeout=5)
    try:
        conn.execute('PRAGMA trusted_schema=OFF')
        conn.execute('PRAGMA foreign_keys=ON')
        if writable:
            result = conn.execute('PRAGMA journal_mode=DELETE').fetchone()
            if result[0].lower() != 'delete':
                raise VaultError('vault requires SQLite rollback journaling')
            conn.execute('PRAGMA synchronous=FULL')
        else:
            conn.execute('PRAGMA query_only=ON')
        return conn
    except BaseException:
        conn.close()
        raise


def metadata(conn):
    try:
        rows = conn.execute('SELECT version,kdf,salt,verify FROM vault_meta').fetchall()
    except sqlite3.Error as exc:
        raise VaultError('invalid or unsupported vault format') from exc
    if len(rows) != 1:
        raise VaultError('invalid vault metadata')
    version, kdf, salt, verifier = rows[0]
    if version != VERSION or kdf != KDF or not isinstance(salt, bytes) or len(salt) != 16 or not isinstance(verifier, bytes) or len(verifier) != 34:
        raise VaultError('unsupported or damaged vault metadata')
    return salt, verifier


def unlock_connection(conn, password):
    salt, verifier = metadata(conn)
    key = derive(password, salt)
    if decrypt(key, verifier) != b'verify':
        raise VaultError('invalid verification record')
    return key


def _integrity(conn):
    if conn.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise VaultError('vault integrity check failed')


def _validate_records(conn, key, allow_missing_totp=False):
    counts = {}
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    for table, field in [('secrets', 'key'), ('totp', 'name')]:
        if table == 'totp' and table not in tables and allow_missing_totp:
            counts[table] = 0
            continue
        count = 0
        for name, blob in conn.execute(f'SELECT {field},blob FROM {table}'):
            if not isinstance(name, str) or not isinstance(blob, bytes):
                raise VaultError('invalid record type')
            try:
                decrypt(key, blob, name.encode()).decode('utf-8')
            except UnicodeError as exc:
                raise VaultError('damaged record encoding') from exc
            count += 1
        counts[table] = count
    return counts


def inspect_snapshot(path, password=None):
    conn = _connect(path)
    try:
        conn.execute('BEGIN')
        _integrity(conn)
        metadata(conn)
        if password is not None:
            return _validate_records(conn, unlock_connection(conn, password))
        return {'format': VERSION, 'authenticated': False}
    finally:
        conn.close()


class VaultStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else Path.home() / '.vault'
        self.path = self.directory / 'vault-v2.db'
        self.legacy = self.directory / 'vault.db'

    @contextmanager
    def locked(self):
        private_dir(self.directory)
        with lock(self.directory / '.vault.lock'):
            yield

    def _require_v2(self):
        if not self.path.exists():
            if self.legacy.exists():
                raise VaultError('legacy vault detected; run ish vault migrate first')
            raise VaultError('vault not initialized; run ish vault init')
        regular_file(self.path)

    @contextmanager
    def session(self, password=None, write=False):
        with self.locked():
            self._require_v2()
            self.path.chmod(0o600)
            # Reads also open read/write so SQLite can recover a hot rollback journal
            # after a killed writer. The directory lock serializes that recovery.
            conn = _connect(self.path, writable=True)
            try:
                conn.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
                key = unlock_connection(conn, password) if password is not None else None
                if password is None:
                    metadata(conn)
                yield conn, key
                if write:
                    _checkpoint('before_commit')
                conn.commit()
                if write:
                    _checkpoint('after_commit')
            except BaseException:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _stage(self):
        fd, path = tempfile.mkstemp(prefix='.vault-v2-stage-', suffix='.db', dir=self.directory)
        os.close(fd)
        return Path(path)

    def _publish(self, stage):
        # The stable directory lock serializes all v2 creators/migrations.
        if self.path.exists() or self.path.is_symlink():
            raise VaultError('v2 vault already exists')
        sync_file(stage)
        _checkpoint('before_publish')
        os.replace(stage, self.path)
        sync_dir(self.directory)
        _checkpoint('after_publish')

    def initialize(self, password):
        if len(password) < 8:
            raise VaultError('master password must contain at least 8 characters')
        with self.locked():
            if any((self.directory / name).exists() or (self.directory / name).is_symlink()
                   for name in ('vault-v2.db', 'vault.db', 'salt', 'verify')):
                raise VaultError('vault files already exist; inspect or migrate them')
            stage = self._stage()
            conn = None
            try:
                salt = os.urandom(16)
                key = derive(password, salt)
                conn = _connect(stage, writable=True)
                conn.execute('BEGIN IMMEDIATE')
                conn.execute('CREATE TABLE secrets(key TEXT PRIMARY KEY, blob BLOB NOT NULL)')
                conn.execute('CREATE TABLE totp(name TEXT PRIMARY KEY, blob BLOB NOT NULL)')
                self._add_metadata(conn, salt, encrypt(key, b'verify'))
                conn.commit()
                conn.close()
                conn = None
                inspect_snapshot(stage, password)
                self._publish(stage)
            finally:
                if conn is not None:
                    conn.close()
                stage.unlink(missing_ok=True)

    @staticmethod
    def _add_metadata(conn, salt, verifier):
        conn.execute('CREATE TABLE vault_meta(id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, kdf TEXT NOT NULL, salt BLOB NOT NULL, verify BLOB NOT NULL)')
        conn.execute('INSERT INTO vault_meta VALUES (1,?,?,?,?)', (VERSION, KDF, salt, verifier))

    def migrate(self, password):
        with self.locked():
            if self.path.exists():
                # Idempotence still requires a valid password and authenticated data.
                return inspect_snapshot(self.path, password)
            regular_file(self.legacy)
            salt = regular_file(self.directory / 'salt').read_bytes()
            verifier = regular_file(self.directory / 'verify').read_bytes()
            if len(salt) != 16 or len(verifier) != 34:
                raise VaultError('legacy metadata is invalid')
            key = derive(password, salt)
            if decrypt(key, verifier) != b'verify':
                raise VaultError('legacy password verification failed')
            stage = self._stage()
            source = target = None
            try:
                source = _connect(self.legacy)
                # One read transaction pins a consistent legacy snapshot.
                source.execute('BEGIN')
                objects = source.execute("SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
                if any(kind != 'table' or name not in {'secrets', 'totp'} for kind, name in objects):
                    raise VaultError('unexpected legacy schema; migration refused')
                target = _connect(stage, writable=True)
                source.backup(target)
                source.close(); source = None
                _integrity(target)
                counts = _validate_records(target, key, allow_missing_totp=True)
                target.execute('BEGIN IMMEDIATE')
                target.execute('CREATE TABLE IF NOT EXISTS totp(name TEXT PRIMARY KEY, blob BLOB NOT NULL)')
                self._add_metadata(target, salt, verifier)
                _checkpoint('migration_metadata')
                target.commit()
                target.close(); target = None
                inspect_snapshot(stage, password)
                self._publish(stage)
                return counts
            finally:
                if source is not None: source.close()
                if target is not None: target.close()
                stage.unlink(missing_ok=True)

    @staticmethod
    def _table(kind):
        if kind == 'secret': return 'secrets', 'key'
        if kind == 'totp': return 'totp', 'name'
        raise VaultError('unknown record type')

    def put(self, name, value, password, kind='secret'):
        if not isinstance(name, str) or not name or len(name) > 256 or any(ord(c) < 32 for c in name):
            raise VaultError('entry name must be 1-256 printable characters')
        table, field = self._table(kind)
        with self.session(password, write=True) as (conn, key):
            blob = encrypt(key, value.encode(), name.encode())
            conn.execute(f'INSERT OR REPLACE INTO {table}({field},blob) VALUES (?,?)', (name, blob))

    def get(self, name, password, kind='secret'):
        table, field = self._table(kind)
        with self.session(password) as (conn, key):
            row = conn.execute(f'SELECT blob FROM {table} WHERE {field}=?', (name,)).fetchone()
            if row is None: raise VaultError('entry not found')
            return decrypt(key, row[0], name.encode()).decode()

    def names(self, kind='secret'):
        table, field = self._table(kind)
        with self.session() as (conn, key):
            return [r[0] for r in conn.execute(f'SELECT {field} FROM {table} ORDER BY {field}')]

    def values(self, password, kind='secret', name=None):
        table, field = self._table(kind)
        with self.session(password) as (conn, key):
            query = f'SELECT {field},blob FROM {table}'
            rows = conn.execute(query + (f' WHERE {field}=?' if name else f' ORDER BY {field}'), (name,) if name else ())
            return [(n, decrypt(key, b, n.encode()).decode()) for n, b in rows]

    def delete(self, name, password, kind='secret'):
        table, field = self._table(kind)
        with self.session(password, write=True) as (conn, key):
            if conn.execute(f'DELETE FROM {table} WHERE {field}=?', (name,)).rowcount != 1:
                raise VaultError('entry not found')

    def rotate(self, old_password, new_password):
        if len(new_password) < 8 or old_password == new_password:
            raise VaultError('new password must be different and at least 8 characters')
        with self.session(old_password, write=True) as (conn, old_key):
            salt = os.urandom(16)
            new_key = derive(new_password, salt)
            for table, field in [('secrets', 'key'), ('totp', 'name')]:
                rows = conn.execute(f'SELECT {field},blob FROM {table}').fetchall()
                for name, blob in rows:
                    value = decrypt(old_key, blob, name.encode())
                    fresh = encrypt(new_key, value, name.encode())
                    if decrypt(new_key, fresh, name.encode()) != value:
                        raise VaultError('record verification failed')
                    conn.execute(f'UPDATE {table} SET blob=? WHERE {field}=?', (fresh, name))
                    _checkpoint('rotated_record')
            conn.execute('UPDATE vault_meta SET salt=?,verify=? WHERE id=1', (salt, encrypt(new_key, b'verify')))
            _checkpoint('rotated_metadata')
            _validate_records(conn, unlock_connection(conn, new_password))

    def check(self, password=None):
        with self.session(password) as (conn, key):
            _integrity(conn)
            if password is not None:
                return _validate_records(conn, key)
            return {'format': VERSION, 'integrity': 'ok', 'authenticated': False}

    def snapshot(self, destination, password):
        destination = Path(destination)
        with self.session(password) as (conn, key):
            _validate_records(conn, key)
            fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            target = None
            try:
                target = _connect(destination, writable=True)
                conn.backup(target)
                target.close(); target = None
                inspect_snapshot(destination, password)
                sync_file(destination)
            except BaseException:
                if target is not None: target.close()
                destination.unlink(missing_ok=True)
                raise
