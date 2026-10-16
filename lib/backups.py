"""Private catalogue of verified local snapshots; no in-place restore or pruning."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid
from .storage import StorageError, private_dir, regular_file, read_json, write_json_new, sync_dir, sync_file, publish_new
from .workspaces import state_root, resolve_database
from .db import SQLiteDB, DBError
from .vault_store import VaultStore, inspect_snapshot
from . import backup_crypto

IDENTIFIER = re.compile(r'\d{8}T\d{6}Z-[a-f0-9]{16}\Z')


def root():
    return private_dir(state_root() / 'backups')


def digest(path):
    result = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def load(identifier):
    if not IDENTIFIER.fullmatch(identifier):
        raise StorageError('invalid backup ID')
    directory = root() / identifier
    if directory.is_symlink(): raise StorageError('backup directory cannot be a symlink')
    info = read_json(directory / 'manifest.json')
    validate_manifest(info, identifier)
    expected = info['payload']
    regular_file(directory / expected)
    return info


def validate_manifest(info, identifier):
    if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
        raise StorageError('invalid backup ID')
    if type(info.get('version')) is not int or info.get('version') != 1 or info.get('id') != identifier or info.get('kind') not in {'database', 'vault'}:
        raise StorageError('unsupported backup manifest')
    for field in ('source', 'created_utc'):
        if not isinstance(info.get(field), str) or not info[field] or len(info[field]) > 4096:
            raise StorageError('invalid descriptive backup metadata')
    if not isinstance(info.get('encrypted'), bool): raise StorageError('invalid encryption flag')
    expected = 'payload.crypt' if info['encrypted'] else 'payload.db'
    if info.get('payload') != expected or not isinstance(info.get('sha256'), str) or not re.fullmatch('[a-f0-9]{64}', info['sha256']):
        raise StorageError('invalid payload metadata')
    if type(info.get('bytes')) is not int or info['bytes'] < 0:
        raise StorageError('invalid payload size')

def _validate(path, kind, password=None):
    if kind == 'vault':
        if password is None: raise StorageError('vault password is required to verify all records')
        return inspect_snapshot(path, password)
    with SQLiteDB(path) as db:
        if not db.integrity_check(): raise DBError('snapshot integrity check failed')
    return {'integrity': 'ok'}


def create(source, encrypted=False, password=None):
    catalog = root()
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:16]
    final = catalog / identifier
    stage = Path(tempfile.mkdtemp(prefix='.backup-', dir=catalog))
    kind = 'vault' if source == 'vault' else 'database'
    try:
        plain = stage / 'payload.db'
        if kind == 'vault':
            if password is None: raise StorageError('vault password required')
            VaultStore().snapshot(plain, password)
            source_label = 'vault-v2'
        else:
            database = resolve_database(source)
            with SQLiteDB(database) as db:
                if not db.integrity_check(): raise DBError('source integrity check failed')
                db.backup(plain)
            source_label = str(database)
        _validate(plain, kind, password)
        payload = plain
        if encrypted:
            payload = stage / 'payload.crypt'
            backup_crypto.encrypt_file(plain, payload)
            # Actually decrypt and validate before recording a successful backup.
            recovered = stage / 'roundtrip.db'
            backup_crypto.decrypt_file(payload, recovered)
            if digest(recovered) != digest(plain): raise StorageError('encryption round-trip mismatch')
            _validate(recovered, kind, password)
            recovered.unlink()
            plain.unlink()
        sync_file(payload)
        info = {'version': 1, 'id': identifier, 'kind': kind,
                'created_utc': datetime.now(timezone.utc).isoformat(),
                'source': source_label, 'encrypted': bool(encrypted),
                'payload': payload.name, 'sha256': digest(payload), 'bytes': payload.stat().st_size}
        write_json_new(stage / 'manifest.json', info)
        sync_dir(stage)
        if final.exists(): raise StorageError('backup ID collision')
        os.rename(stage, final)
        sync_dir(catalog)
        return info
    finally:
        if stage.exists(): shutil.rmtree(stage)


@contextmanager
def verified_copy(identifier, password=None):
    info = load(identifier)
    source = root() / identifier / info['payload']
    with tempfile.TemporaryDirectory(prefix='.verify-', dir=root()) as tmp:
        temp = Path(tmp)
        copy = temp / 'payload'
        # Verify the actual private copy used for restore, not a separate earlier read.
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as inp, open(copy, 'xb') as out:
            os.chmod(copy, 0o600)
            shutil.copyfileobj(inp, out, 1024 * 1024)
        if copy.stat().st_size != info['bytes'] or digest(copy) != info['sha256']:
            raise StorageError('backup checksum mismatch')
        plain = copy
        if info['encrypted']:
            plain = temp / 'verified.db'
            backup_crypto.decrypt_file(copy, plain)
        result = _validate(plain, info['kind'], password)
        yield info, plain, result


def verify(identifier, password=None):
    with verified_copy(identifier, password) as (info, path, result):
        return {'id': identifier, 'verified': True, 'encrypted': info['encrypted'],
                'kind': info['kind'], 'checks': result}


def restore(identifier, destination, password=None):
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink(): raise StorageError('restore destination must be new')
    if destination.resolve().is_relative_to((Path.home() / '.vault').resolve()):
        raise StorageError('restore to a separate location, never into the active vault')
    if not destination.parent.is_dir(): raise StorageError('restore parent directory does not exist')
    with verified_copy(identifier, password) as (info, plain, result):
        if info['kind'] == 'vault':
            # mkdir is exclusive: no existing target is ever replaced.
            destination.mkdir(mode=0o700)
            target = destination / 'vault-v2.db'
        else:
            target = destination
        with tempfile.TemporaryDirectory(prefix='.restore-', dir=target.parent) as tmp:
            staged = Path(tmp) / 'data.db'
            with open(plain, 'rb') as inp, open(staged, 'xb') as out:
                os.chmod(staged, 0o600)
                shutil.copyfileobj(inp, out, 1024 * 1024)
            if digest(staged) != digest(plain): raise StorageError('restored copy checksum mismatch')
            _validate(staged, info['kind'], password)
            publish_new(staged, target)
        return {'id': identifier, 'restored_to': str(target), 'verified': True,
                'activation': 'not activated' if info['kind'] == 'vault' else 'new database file'}


def listing():
    result = []
    for directory in sorted(root().iterdir()):
        if not IDENTIFIER.fullmatch(directory.name): continue
        try:
            info = load(directory.name)
            result.append({k: info[k] for k in ('id', 'kind', 'encrypted', 'created_utc', 'source')})
        except (StorageError, OSError):
            result.append({'id': directory.name, 'status': 'invalid manifest or missing payload'})
    return result
