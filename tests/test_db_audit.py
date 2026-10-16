import json
import pytest
from lib.db_audit import AuditLog


def test_audit_excludes_data(tmp_path):
    path = tmp_path / 'audit.jsonl'
    log = AuditLog(path)
    log.record('query', database='private-name', metadata={'password': 'secret', 'sql': 'SELECT private'})
    event = json.loads(path.read_text())
    assert set(event) == {'action', 'success', 'timestamp'}
    assert path.stat().st_mode & 0o777 == 0o600


def test_audit_rejects_symlink(tmp_path):
    target = tmp_path / 'target'
    target.write_text('untouched')
    link = tmp_path / 'log'
    link.symlink_to(target)
    with pytest.raises(OSError):
        AuditLog(link).record('query')
    assert target.read_text() == 'untouched'
