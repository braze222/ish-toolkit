"""Portable, uncompressed .ishbackup bundles with strict member validation."""
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
from . import backups, backup_crypto
from .storage import StorageError, private_dir, sync_dir, sync_file, write_json_new, lock


def _open_bundle(path):
    archive = tarfile.open(path, 'r:')  # No compressed tar bombs or extraction API.
    try:
        members = []
        for item in archive:
            if len(members) == 2: raise StorageError('bundle has unexpected extra members')
            if item.type not in (tarfile.REGTYPE, tarfile.AREGTYPE) or item.sparse or item.name not in {'manifest.json', 'payload.db', 'payload.crypt'}:
                raise StorageError('bundle contains an unsafe or unsupported member')
            if item.name in {m.name for m in members}: raise StorageError('duplicate bundle member')
            members.append(item)
        manifest = next((m for m in members if m.name == 'manifest.json'), None)
        if len(members) != 2 or manifest is None or manifest.size > 16384:
            raise StorageError('invalid bundle structure')
        info = json.loads(archive.extractfile(manifest).read().decode('utf-8'))
        if not isinstance(info, dict): raise StorageError('invalid bundle manifest')
        # Validate schema through the same validator used by the local catalogue.
        backups.validate_manifest(info, info.get('id', ''))
        payload = next(m for m in members if m.name != 'manifest.json')
        if payload.name != info['payload'] or payload.size != info['bytes']:
            raise StorageError('bundle payload metadata mismatch')
        if payload.size > backup_crypto.LIMIT + 84:
            raise StorageError('bundle exceeds supported size')
        return archive, info, payload
    except BaseException:
        archive.close(); raise


def inspect_bundle(path):
    archive, info, _ = _open_bundle(path)
    archive.close()
    return info


def _check_payload(info, payload, password):
    if payload.stat().st_size != info['bytes'] or backups.digest(payload) != info['sha256']:
        raise StorageError('backup checksum mismatch')
    if info['encrypted']:
        with tempfile.TemporaryDirectory(prefix='.decrypt-', dir=payload.parent) as directory:
            plain = Path(directory) / 'verified.db'
            backup_crypto.decrypt_file(payload, plain)
            backups._validate(plain, info['kind'], password)
    else:
        backups._validate(payload, info['kind'], password)


def export_bundle(identifier, destination, password=None):
    info = backups.load(identifier)
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink(): raise StorageError('export destination must be new')
    with tempfile.TemporaryDirectory(prefix='.export-', dir=backups.root()) as directory:
        stage = Path(directory)
        payload = stage / info['payload']
        with open(backups.root()/identifier/info['payload'], 'rb') as inp, payload.open('xb') as out:
            payload.chmod(0o600); shutil.copyfileobj(inp, out, 1024*1024)
        _check_payload(info, payload, password)
        write_json_new(stage/'manifest.json', info)
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, 'wb') as output:
                with tarfile.open(fileobj=output, mode='w') as archive:
                    for name in ('manifest.json', info['payload']):
                        entry = archive.gettarinfo(str(stage/name), arcname=name)
                        entry.uid = entry.gid = 0; entry.uname = entry.gname = ''
                        entry.mode = 0o600
                        with (stage/name).open('rb') as data: archive.addfile(entry, data)
                output.flush(); os.fsync(output.fileno())
        except BaseException:
            destination.unlink(missing_ok=True); raise
    return {'id': identifier, 'exported_to': str(destination), 'verified': True}


def import_bundle(path, password=None):
    archive, info, member = _open_bundle(Path(path).expanduser())
    catalog = backups.root()
    stage = Path(tempfile.mkdtemp(prefix='.import-', dir=catalog))
    try:
        final = catalog / info['id']
        payload = stage / info['payload']
        with archive, archive.extractfile(member) as inp, payload.open('xb') as out:
            payload.chmod(0o600); shutil.copyfileobj(inp, out, 1024*1024)
            out.flush(); os.fsync(out.fileno())
        _check_payload(info, payload, password)
        write_json_new(stage/'manifest.json', info)
        sync_dir(stage)
        with lock(catalog / '.import.lock'):
            if final.exists() or final.is_symlink(): raise StorageError('backup ID already exists; import never overwrites')
            os.rename(stage, final); sync_dir(catalog)
        return {'id': info['id'], 'imported': True, 'verified': True}
    finally:
        archive.close()
        if stage.exists(): shutil.rmtree(stage)
