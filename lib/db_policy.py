"""SQLite policy. The SQLite authorizer is the enforcement boundary."""
from dataclasses import dataclass
import re
import sqlite3


class PolicyError(Exception):
    pass


@dataclass(frozen=True)
class DBPolicy:
    read_only: bool = True
    allow_destructive: bool = False


# Strip quoted values/identifiers and comments before the early UX check.
_TOKENS = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`(?:``|[^`])*`|\[[^\]]*\]|--[^\n]*|/\*.*?\*/", re.S)
_WRITE = re.compile(r'\b(CREATE|DROP|DELETE|UPDATE|INSERT|REPLACE|ALTER|VACUUM|REINDEX|ANALYZE)\b', re.I)


def validate_sql(sql, policy):
    if not isinstance(sql, str) or not sql.strip():
        raise PolicyError('SQL must be a nonempty string')
    plain = _TOKENS.sub(' ', sql).strip()
    if not plain or re.search(r';\s*\S', plain):
        raise PolicyError('Exactly one SQL statement is required')
    if re.search(r'\b(ATTACH|DETACH)\b', plain, re.I):
        raise PolicyError('Attached databases are not supported')
    if (policy.read_only or not policy.allow_destructive) and _WRITE.search(plain):
        raise PolicyError('Writes require --write and --allow-destructive')


SAFE_PRAGMAS = {'table_info', 'table_xinfo', 'index_info', 'index_xinfo',
                'index_list', 'foreign_key_list', 'integrity_check', 'quick_check'}
READ_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
                sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
BLOCKED_ACTIONS = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH,
                   sqlite3.SQLITE_CREATE_VTABLE, sqlite3.SQLITE_DROP_VTABLE}


def authorizer(policy):
    def authorize(action, arg1, arg2, database, trigger):
        if action in BLOCKED_ACTIONS:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or '').lower() in {'load_extension', 'writefile', 'readfile'}:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_PRAGMA:
            return sqlite3.SQLITE_OK if (arg1 or '').lower() in SAFE_PRAGMAS else sqlite3.SQLITE_DENY
        if policy.read_only or not policy.allow_destructive:
            if action not in READ_ACTIONS:
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    return authorize
