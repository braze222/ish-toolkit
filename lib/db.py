"""Local SQLite only; no shell, network, or credential handling."""
import os
import sqlite3
from pathlib import Path
from .db_policy import DBPolicy, PolicyError, authorizer, validate_sql


class DBError(Exception):
    pass


class Database:
    # Preserve the original library API; CLI uses SQLiteDB's read-only default.
    def __init__(self, path, readonly=False, policy=None):
        self.path = Path(path).expanduser().absolute()
        self.policy = policy or DBPolicy(readonly, not readonly)
        self.readonly = self.policy.read_only or not self.policy.allow_destructive
        self.conn = None

    def connect(self):
        if self.conn is not None:
            return self
        try:
            if not self.path.exists():
                if self.readonly:
                    raise DBError('database does not exist')
                self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            uri = self.path.resolve().as_uri() + ('?mode=ro' if self.readonly else '?mode=rw')
            self.conn = sqlite3.connect(uri, uri=True, timeout=5)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute('PRAGMA foreign_keys=ON')
            self.conn.execute('PRAGMA trusted_schema=OFF')
            if self.readonly:
                self.conn.execute('PRAGMA query_only=ON')
            self.conn.set_authorizer(authorizer(self.policy))
            return self
        except (sqlite3.Error, OSError) as exc:
            self.close()
            raise DBError('database connection failed') from exc

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def execute(self, sql, params=()):
        try:
            validate_sql(sql, self.policy)
        except PolicyError as exc:
            raise DBError(str(exc)) from exc
        self.connect()
        try:
            return self.conn.execute(sql, params)
        except sqlite3.Error as exc:
            # SQLite messages can echo data values; keep the public message generic.
            raise DBError('SQL failed or was denied by policy') from exc

    def query(self, sql, params=()):
        return [dict(row) for row in self.execute(sql, params).fetchall()]

    def execute_write(self, sql, params=()):
        if self.readonly:
            raise DBError('database is read-only')
        try:
            cursor = self.execute(sql, params)
            self.conn.commit()
            return cursor
        except Exception:
            if self.conn is not None:
                self.conn.rollback()
            raise

    def transaction(self):
        self.connect()
        if self.readonly:
            raise DBError('database is read-only')
        return self.conn

    def integrity_check(self):
        rows = self.query('PRAGMA integrity_check')
        return len(rows) == 1 and list(rows[0].values()) == ['ok']

    def tables(self):
        return self.query("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")

    def schema(self, table):
        return self.query('SELECT * FROM pragma_table_info(?)', (table,))

    def backup(self, destination):
        """Consistent snapshot including committed WAL data; never overwrite."""
        self.connect()
        destination = Path(destination).expanduser().absolute()
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        target = None
        try:
            target = sqlite3.connect(destination)
            self.conn.backup(target)
            result = target.execute('PRAGMA integrity_check').fetchall()
            if result != [('ok',)]:
                raise DBError('backup integrity check failed')
        except Exception:
            if target is not None:
                target.close()
                target = None
            destination.unlink()
            raise
        finally:
            if target is not None:
                target.close()

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc, traceback):
        try:
            if self.conn is not None and not self.readonly:
                if exc_type is None:
                    self.conn.commit()
                else:
                    self.conn.rollback()
        finally:
            self.close()
        return False


class SQLiteDB(Database):
    def __init__(self, path, policy=None):
        super().__init__(path, policy=policy or DBPolicy())
