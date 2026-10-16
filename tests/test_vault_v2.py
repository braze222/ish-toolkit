import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import textwrap
import pytest
from lib.vault_store import VaultStore, VaultError, derive, encrypt, inspect_snapshot
from lib.storage import StorageError, lock

OLD = 'Old-master-password-123!'
NEW = 'New-master-password-456!'
ROOT = Path(__file__).resolve().parents[1]


def legacy(directory, totp=True):
    directory.mkdir(mode=0o700)
    salt = os.urandom(16)
    key = derive(OLD, salt)
    (directory / 'salt').write_bytes(salt)
    (directory / 'verify').write_bytes(encrypt(key, b'verify'))
    with sqlite3.connect(directory / 'vault.db') as conn:
        conn.execute('CREATE TABLE secrets(key TEXT PRIMARY KEY, blob BLOB)')
        conn.execute('INSERT INTO secrets VALUES (?,?)', ('example', encrypt(key, b'legacy-value', b'example')))
        if totp:
            conn.execute('CREATE TABLE totp(name TEXT PRIMARY KEY, blob BLOB)')
            conn.execute('INSERT INTO totp VALUES (?,?)', ('account', encrypt(key, b'JBSWY3DPEHPK3PXP', b'account')))
    for name in ('salt', 'verify', 'vault.db'): (directory / name).chmod(0o600)


@pytest.mark.parametrize('with_totp', [True, False])
def test_migrate_preserves_legacy_and_records(tmp_path, with_totp):
    directory = tmp_path / 'vault'
    legacy(directory, with_totp)
    original = {p.name: p.read_bytes() for p in directory.iterdir()}
    store = VaultStore(directory)
    counts = store.migrate(OLD)
    assert counts == {'secrets': 1, 'totp': int(with_totp)}
    assert store.get('example', OLD) == 'legacy-value'
    if with_totp: assert store.get('account', OLD, 'totp') == 'JBSWY3DPEHPK3PXP'
    for name, value in original.items(): assert (directory / name).read_bytes() == value
    assert store.migrate(OLD) == counts
    with pytest.raises(VaultError): store.migrate('wrong')


def test_legacy_mutation_refused_until_explicit_migration(tmp_path):
    legacy(tmp_path / 'vault')
    store = VaultStore(tmp_path / 'vault')
    with pytest.raises(VaultError, match='migrate'): store.put('x', 'y', OLD)
    with pytest.raises(VaultError): store.initialize(OLD)
    assert not store.path.exists()


def test_wrong_password_and_corrupt_record_do_not_publish(tmp_path):
    legacy(tmp_path / 'vault')
    store = VaultStore(tmp_path / 'vault')
    with pytest.raises(VaultError): store.migrate('wrong')
    assert not store.path.exists()
    with sqlite3.connect(store.legacy) as conn: conn.execute("UPDATE secrets SET blob=x'0001'")
    with pytest.raises(VaultError): store.migrate(OLD)
    assert not store.path.exists()


def test_unknown_schema_refused(tmp_path):
    legacy(tmp_path / 'vault')
    with sqlite3.connect(tmp_path / 'vault/vault.db') as conn: conn.execute('CREATE TABLE unknown(x)')
    with pytest.raises(VaultError, match='schema'): VaultStore(tmp_path / 'vault').migrate(OLD)


def kill_worker(directory, operation, stage):
    # Kill at a deterministic boundary in a separate process without cleanup.
    program = textwrap.dedent('''
        import os, sys
        from pathlib import Path
        from lib import vault_store as module
        from lib.vault_store import VaultStore
        directory, operation, stage = sys.argv[1:]
        def checkpoint(current):
            if current == stage: os._exit(77)
        module._checkpoint = checkpoint
        store = VaultStore(Path(directory))
        if operation == 'rotate': store.rotate('Old-master-password-123!', 'New-master-password-456!')
        else: store.migrate('Old-master-password-123!')
    ''')
    result = subprocess.run([sys.executable, '-c', program, str(directory), operation, stage], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 77, result.stderr


@pytest.mark.parametrize('stage,expected', [('rotated_record', OLD), ('rotated_metadata', OLD), ('before_commit', OLD), ('after_commit', NEW)])
def test_process_death_rotation_recovers_single_consistent_state(tmp_path, stage, expected):
    store = VaultStore(tmp_path / 'vault')
    store.initialize(OLD)
    store.put('example', 'secret-value', OLD)
    store.put('account', 'JBSWY3DPEHPK3PXP', OLD, 'totp')
    kill_worker(store.directory, 'rotate', stage)
    # The first read must recover the hot journal itself, not require a write first.
    assert store.get('example', expected) == 'secret-value'
    assert store.get('account', expected, 'totp') == 'JBSWY3DPEHPK3PXP'
    assert store.check(expected) == {'secrets': 1, 'totp': 1}
    with pytest.raises(VaultError): store.get('example', NEW if expected == OLD else OLD)


@pytest.mark.parametrize('stage,published', [('migration_metadata', False), ('before_publish', False), ('after_publish', True)])
def test_process_death_migration_is_retryable(tmp_path, stage, published):
    legacy(tmp_path / 'vault')
    store = VaultStore(tmp_path / 'vault')
    original = {name: (store.directory/name).read_bytes() for name in ('vault.db','salt','verify')}
    kill_worker(store.directory, 'migrate', stage)
    assert store.path.exists() == published
    store.migrate(OLD)
    assert store.get('example', OLD) == 'legacy-value'
    for name, value in original.items(): assert (store.directory/name).read_bytes() == value


def test_lock_blocks_competing_operation_and_releases(tmp_path):
    store = VaultStore(tmp_path / 'vault')
    store.initialize(OLD)
    with lock(store.directory / '.vault.lock'):
        with pytest.raises(StorageError, match='another'): store.names()
    assert store.names() == []


def test_write_failure_rolls_back(tmp_path, monkeypatch):
    from lib import vault_store
    store = VaultStore(tmp_path / 'vault'); store.initialize(OLD); store.put('a','value',OLD)
    def fail(stage):
        if stage == 'rotated_metadata': raise OSError('simulated disk failure')
    monkeypatch.setattr(vault_store, '_checkpoint', fail)
    with pytest.raises(OSError): store.rotate(OLD, NEW)
    assert store.get('a',OLD) == 'value'


def test_snapshot_survives_subsequent_rotation(tmp_path):
    store = VaultStore(tmp_path / 'vault'); store.initialize(OLD);store.put('a','value',OLD)
    snapshot = tmp_path / 'copy.db'; store.snapshot(snapshot, OLD)
    store.rotate(OLD,NEW)
    assert inspect_snapshot(snapshot,OLD) == {'secrets':1,'totp':0}
    with pytest.raises(VaultError): inspect_snapshot(snapshot,NEW)


def test_bad_new_password_changes_nothing(tmp_path):
    store = VaultStore(tmp_path / 'vault'); store.initialize(OLD)
    with pytest.raises(VaultError): store.rotate(OLD, 'short')
    with pytest.raises(VaultError): store.rotate(OLD, OLD)
    assert store.check(OLD) == {'secrets':0,'totp':0}


def test_symlink_vault_root_refused(tmp_path):
    target=tmp_path/'target';target.mkdir();link=tmp_path/'link';link.symlink_to(target)
    with pytest.raises(StorageError): VaultStore(link).initialize(OLD)
    assert not list(target.iterdir())


def test_migration_includes_wal_records(tmp_path):
    legacy(tmp_path/'vault')
    directory=tmp_path/'vault'
    salt=(directory/'salt').read_bytes();key=derive(OLD,salt)
    writer=sqlite3.connect(directory/'vault.db')
    try:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute('INSERT INTO secrets VALUES (?,?)',('wal',encrypt(key,b'committed-wal',b'wal')))
        writer.commit()
        store=VaultStore(directory);store.migrate(OLD)
        assert store.get('wal',OLD)=='committed-wal'
        store.rotate(OLD,NEW)
        assert store.get('wal',NEW)=='committed-wal'
    finally:writer.close()


def test_cli_can_check_separate_restored_vault(tmp_path):
    store=VaultStore(tmp_path/'restored');store.initialize(OLD)
    result=subprocess.run([sys.executable,str(ROOT/'tools/ish.py'),'vault','--directory',str(store.directory),'check'],capture_output=True,text=True,cwd=tmp_path)
    assert result.returncode==0,result.stderr
    assert '"format": 2' in result.stdout
