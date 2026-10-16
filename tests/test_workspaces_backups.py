import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import pytest
from lib import workspaces, backups
from lib.db import SQLiteDB, DBError
from lib.db_policy import DBPolicy
from lib.storage import StorageError
from lib.vault_store import VaultStore, VaultError
from lib import backup_crypto

ROOT = Path(__file__).resolve().parents[1]
PW = 'Backup-vault-password-123!'


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))


def database():
    info = workspaces.create('notes')
    with SQLiteDB(info['database'], DBPolicy(False, True)) as db:
        db.execute('CREATE TABLE notes(value TEXT)')
        db.execute('INSERT INTO notes VALUES (?)', ('expected',))
    return Path(info['database'])


def keypair():
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    directory = Path.home()/'.crypt'; directory.mkdir(mode=0o700, exist_ok=True)
    path = directory/'id.key'
    path.write_bytes(X25519PrivateKey.generate().private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption()))
    path.chmod(0o600)


def test_workspace_create_register_resolve_status(tmp_path):
    path = database()
    assert workspaces.resolve_database('@notes') == path
    assert workspaces.names() == ['notes']
    assert workspaces.status('notes')['tables'] == ['notes']
    workspaces.create('alias',path)
    assert workspaces.resolve_database('@alias') == path
    with pytest.raises(StorageError): workspaces.create('notes')
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('name',['../escape','a/b','UPPER','', 'x'*49,'@notes'])
def test_names_reject_traversal(name):
    with pytest.raises(StorageError): workspaces.create(name)


def test_register_missing_database_never_creates(tmp_path):
    with pytest.raises(DBError): workspaces.create('missing',tmp_path/'missing.db')
    assert not (tmp_path/'missing.db').exists()


def test_workspace_cannot_target_active_vault(tmp_path):
    with pytest.raises(StorageError): workspaces.create('bad',tmp_path/'.vault/vault-v2.db')


@pytest.mark.parametrize('encrypted', [False, True])
def test_backup_roundtrip_and_no_clobber(tmp_path,encrypted):
    source=database()
    if encrypted: keypair()
    info=backups.create('@notes', encrypted)
    assert backups.verify(info['id'])['verified']
    out=tmp_path/'restored.db';backups.restore(info['id'],out)
    with SQLiteDB(out) as db: assert db.query('SELECT * FROM notes')==[{'value':'expected'}]
    with pytest.raises(StorageError): backups.restore(info['id'],out)
    assert out.stat().st_mode & 0o777 == 0o600
    assert backups.listing()[0]['id']==info['id']
    if encrypted: assert not (backups.root()/info['id']/'payload.db').exists()


def test_tamper_detected_before_restore(tmp_path):
    database();info=backups.create('@notes')
    payload=backups.root()/info['id']/info['payload']
    with open(payload,'ab') as h:h.write(b'changed')
    target=tmp_path/'out.db'
    with pytest.raises(StorageError,match='checksum'):backups.restore(info['id'],target)
    assert not target.exists()


def test_encryption_wrong_key_fails(tmp_path):
    database();keypair();info=backups.create('@notes',True);keypair()
    with pytest.raises(StorageError,match='decryption'):backups.verify(info['id'])


def test_manifest_cannot_escape_directory(tmp_path):
    database();info=backups.create('@notes')
    path=backups.root()/info['id']/'manifest.json'
    data=json.loads(path.read_text());data['payload']='../../secret';path.write_text(json.dumps(data))
    with pytest.raises(StorageError):backups.verify(info['id'])


def test_payload_symlink_rejected(tmp_path):
    database();info=backups.create('@notes'); payload=backups.root()/info['id']/info['payload']
    other=tmp_path/'other';payload.rename(other);payload.symlink_to(other)
    with pytest.raises(StorageError):backups.verify(info['id'])


def test_vault_backup_authenticates_records_and_restores_separately(tmp_path):
    keypair();store=VaultStore();store.initialize(PW);store.put('name','private-value',PW)
    store.put('account','JBSWY3DPEHPK3PXP',PW,'totp')
    info=backups.create('vault',True,PW)
    with pytest.raises(VaultError):backups.verify(info['id'],'wrong')
    result=backups.verify(info['id'],PW)
    assert result['checks']=={'secrets':1,'totp':1}
    out=tmp_path/'recovered';backups.restore(info['id'],out,PW)
    assert VaultStore(out).get('name',PW)=='private-value'
    assert VaultStore().get('name',PW)=='private-value'
    with pytest.raises(StorageError):backups.restore(info['id'],tmp_path/'.vault/new',PW)


def test_plain_db_backup_has_consistent_wal(tmp_path):
    source=database();other=sqlite3.connect(source)
    try:
        other.execute('PRAGMA journal_mode=WAL')
        other.execute('INSERT INTO notes VALUES (?)',('wal-row',));other.commit()
        info=backups.create('@notes');out=tmp_path/'restored.db';backups.restore(info['id'],out)
        with SQLiteDB(out) as db:assert len(db.query('SELECT * FROM notes'))==2
    finally:other.close()


def test_encryption_limit_fails_without_success_catalogue(monkeypatch):
    database();keypair();monkeypatch.setattr(backup_crypto,'LIMIT',10)
    with pytest.raises(StorageError):backups.create('@notes',True)
    assert backups.listing()==[]


def test_cli_workspace_backup_flow(tmp_path):
    def call(*args):
        return subprocess.run([sys.executable,str(ROOT/'tools/ish.py'),*map(str,args)],text=True,capture_output=True,cwd=tmp_path)
    assert call('workspace','create','example').returncode==0
    assert call('db','tables','@example').returncode==0
    result=call('backup','create','@example');assert result.returncode==0,result.stderr
    identifier=json.loads(result.stdout)['id']
    assert call('backup','verify',identifier).returncode==0
    preview=call('backup','restore',identifier,'--to',tmp_path/'restored.db','--preview')
    assert preview.returncode==0 and not (tmp_path/'restored.db').exists()
    assert call('backup','restore',identifier,'--to',tmp_path/'restored.db').returncode==0
    assert call('backup','restore',identifier,'--to',tmp_path/'restored.db').returncode==1
    assert call('workspace','open','example').returncode==0
    assert call('--version').stdout.strip()=='ish-toolkit 3.0.0-preview'
