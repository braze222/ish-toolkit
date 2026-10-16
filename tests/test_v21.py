import errno
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tracemalloc
import pytest
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from lib import backup_crypto as crypto, backups, keys, recovery, transfer, workspaces
from lib.storage import StorageError
from lib.vault_store import VaultStore, VaultError

ROOT = Path(__file__).resolve().parents[1]
PW = 'vault-old-password!'
NEW = 'vault-new-password!'
KEYPW = 'crypt-key-password!'

@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    directory = tmp_path/'.crypt';directory.mkdir(mode=0o700)
    key = X25519PrivateKey.generate()
    path = directory/'id.key'
    path.write_bytes(key.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption()))
    path.chmod(0o600)
    return tmp_path


def test_key_protect_preserves_identity_and_old_ciphertext(home):
    source=home/'source';source.write_bytes(b'important')
    crypto.encrypt_file(source,home/'encrypted')
    before=keys.load().public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    keys.protect(KEYPW)
    assert (home/'.crypt/id.key').read_bytes().startswith(b'-----BEGIN ENCRYPTED PRIVATE KEY-----')
    with pytest.raises(StorageError):keys.load(password='wrong')
    key=keys.load(password=KEYPW)
    assert key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)==before
    crypto.decrypt_file(home/'encrypted',home/'out',key)
    assert (home/'out').read_bytes()==b'important'
    keys.protect('replacement-password!',KEYPW)
    with pytest.raises(StorageError):keys.load(password=KEYPW)
    keys.load(password='replacement-password!')


def test_key_protect_failure_keeps_original(home,monkeypatch):
    path=home/'.crypt/id.key';before=path.read_bytes()
    def failed(*args):raise OSError(errno.ENOSPC,'full')
    monkeypatch.setattr(keys.os,'replace',failed)
    with pytest.raises(OSError):keys.protect(KEYPW)
    assert path.read_bytes()==before
    assert not list(path.parent.glob('.protected-key-*'))


def test_stream_above_old_limit_bounded_memory(home):
    source=home/'large'
    with source.open('wb') as handle:
        for _ in range(34):handle.write(b'x'*1024*1024)
    tracemalloc.start()
    try:
        crypto.encrypt_file(source,home/'cipher')
        crypto.decrypt_file(home/'cipher',home/'plain')
        _,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop()
    assert peak<16*1024*1024
    assert backups.digest(source)==backups.digest(home/'plain')


@pytest.mark.parametrize('change',['header','middle','tag','truncated','append'])
def test_stream_tampering_never_publishes(home,change):
    source=home/'source';source.write_bytes(os.urandom(2*1024*1024))
    cipher=home/'cipher';crypto.encrypt_file(source,cipher)
    data=bytearray(cipher.read_bytes())
    if change=='truncated':data=data[:-16]
    elif change=='append':data+=b'extra'
    else:data[{'header':9,'middle':100,'tag':-1}[change]]^=1
    cipher.write_bytes(data)
    with pytest.raises(StorageError):crypto.decrypt_file(cipher,home/'plain')
    assert not (home/'plain').exists()
    assert not list(home.glob('.crypt-*'))


def test_legacy_ciphertext_compatible(home):
    recipient=keys.load();ephemeral=X25519PrivateKey.generate()
    salt=os.urandom(16);nonce=os.urandom(12)
    pub=ephemeral.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    key=crypto._derive(ephemeral.exchange(recipient.public_key()),salt,b'crypt-v1')
    cipher=home/'v1';cipher.write_bytes(crypto.LEGACY+salt+pub+nonce+ChaCha20Poly1305(key).encrypt(nonce,b'old format',None))
    crypto.decrypt_file(cipher,home/'plain')
    assert (home/'plain').read_bytes()==b'old format'


@pytest.mark.parametrize('encrypted',[False,True])
def test_export_import_roundtrip_and_duplicate_refusal(home,encrypted):
    workspaces.create('notes');info=backups.create('@notes',encrypted)
    bundle=home/'portable.ishbackup'
    transfer.export_bundle(info['id'],bundle)
    with pytest.raises(StorageError):transfer.import_bundle(bundle)
    with pytest.raises(StorageError):transfer.export_bundle(info['id'],bundle)
    shutil.rmtree(backups.root()/info['id'])
    assert transfer.import_bundle(bundle)['verified']
    assert backups.verify(info['id'])['verified']


@pytest.mark.parametrize('name,kind',[('../escape',tarfile.REGTYPE),('payload.db',tarfile.SYMTYPE),('manifest.json',tarfile.LNKTYPE)])
def test_import_rejects_unsafe_members(home,name,kind):
    bundle=home/'unsafe'
    with tarfile.open(bundle,'w') as t:
        item=tarfile.TarInfo(name);item.type=kind;item.linkname='/tmp/escape';item.size=0;t.addfile(item,io.BytesIO())
    with pytest.raises(StorageError):transfer.import_bundle(bundle)
    assert backups.listing()==[]


def test_import_corruption_not_published(home):
    workspaces.create('notes');info=backups.create('@notes')
    bundle=home/'portable';transfer.export_bundle(info['id'],bundle)
    shutil.rmtree(backups.root()/info['id'])
    data=bytearray(bundle.read_bytes());data[4096]^=1;bundle.write_bytes(data)
    with pytest.raises((StorageError,tarfile.TarError)):transfer.import_bundle(bundle)
    assert backups.listing()==[]


def vault_backup():
    store=VaultStore();store.initialize(PW);store.put('test','original',PW)
    info=backups.create('vault',password=PW)
    store.rotate(PW,NEW);store.put('test','current',NEW)
    return store,info


def test_recovery_preserves_current_and_activates_snapshot(home):
    store,info=vault_backup()
    with pytest.raises(VaultError):recovery.recover(info['id'],'wrong',NEW)
    with pytest.raises(VaultError):recovery.recover(info['id'],PW,'wrong')
    assert store.get('test',NEW)=='current'
    result=recovery.recover(info['id'],PW,NEW)
    assert store.get('test',PW)=='original'
    assert VaultStore(result['previous_vault']).get('test',NEW)=='current'


@pytest.mark.parametrize('stage,expected_password,expected_value',[
    ('recovery_preserved',NEW,'current'),('recovery_replaced_table',NEW,'current'),
    ('before_commit',NEW,'current'),('after_commit',PW,'original')])
def test_recovery_process_death_is_transactional(home,stage,expected_password,expected_value):
    store,info=vault_backup()
    code='''import os,sys
from lib import recovery, vault_store
def checkpoint(stage):
    if stage == sys.argv[2]: os._exit(77)
recovery._checkpoint=checkpoint
vault_store._checkpoint=checkpoint
recovery.recover(sys.argv[1],sys.argv[3],sys.argv[4])
'''
    result=subprocess.run([sys.executable,'-c',code,info['id'],stage,PW,NEW],cwd=ROOT)
    assert result.returncode==77
    assert store.get('test',expected_password)==expected_value
    preserved=list((home/'.ish-toolkit/recovery').glob('before-*'))
    assert len(preserved)==1
    assert VaultStore(preserved[0]).get('test',NEW)=='current'


def test_recover_into_missing_vault(home):
    store,info=vault_backup();shutil.rmtree(store.directory)
    recovery.recover(info['id'],PW)
    assert VaultStore().get('test',PW)=='original'


def test_cli_portable_backup(home):
    def run(*args):return subprocess.run([sys.executable,str(ROOT/'tools/ish.py'),*map(str,args)],capture_output=True,text=True)
    assert run('workspace','create','notes').returncode==0
    result=run('backup','create','@notes');info=json.loads(result.stdout)
    bundle=home/'exported.ishbackup'
    assert run('backup','export',info['id'],'--to',bundle).returncode==0
    shutil.rmtree(backups.root()/info['id'])
    result=run('backup','import',bundle)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['verified']


def test_protected_key_backup_export_import(home,monkeypatch):
    keys.protect(KEYPW)
    monkeypatch.setattr(keys.getpass,'getpass',lambda prompt: KEYPW)
    store=VaultStore();store.initialize(PW);store.put('secret','value',PW)
    info=backups.create('vault',True,PW)
    assert backups.verify(info['id'],PW)['verified']
    bundle=home/'vault.ishbackup';transfer.export_bundle(info['id'],bundle,PW)
    shutil.rmtree(backups.root()/info['id'])
    transfer.import_bundle(bundle,PW)
    backups.restore(info['id'],home/'recovered',PW)
    assert VaultStore(home/'recovered').get('secret',PW)=='value'


def test_full_selftest_cli(home):
    result=subprocess.run([sys.executable,str(ROOT/'tools/ish.py'),'selftest','--full'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'protected key' in result.stdout
    assert not (home/'.vault').exists()


def test_recovery_cli_preview_and_cancel(home):
    store,info=vault_backup()
    cmd=[sys.executable,str(ROOT/'tools/ish.py'),'backup','recover-vault',info['id']]
    assert subprocess.run(cmd+['--preview'],capture_output=True,text=True).returncode==0
    result=subprocess.run(cmd,input='no\n',capture_output=True,text=True)
    assert result.returncode==1
    assert store.get('test',NEW)=='current'
    assert not (home/'.ish-toolkit/recovery').exists()


def test_incomplete_manifest_refused(home):
    workspaces.create('notes');info=backups.create('@notes')
    path=backups.root()/info['id']/'manifest.json'
    data=json.loads(path.read_text());del data['source'];path.write_text(json.dumps(data))
    with pytest.raises(StorageError):backups.verify(info['id'])
    assert backups.listing()[0]['status']=='invalid manifest or missing payload'
