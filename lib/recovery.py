"""Activate a verified vault snapshot with transactional replacement and rollback copy."""
import os
from pathlib import Path
import shutil
import sqlite3
import uuid
from . import backups
from .storage import private_dir, sync_file, sync_dir, StorageError
from .vault_store import VaultStore, _connect, unlock_connection, _validate_records, _checkpoint


def recover(identifier, snapshot_password, current_password=None):
    with backups.verified_copy(identifier, snapshot_password) as (info, plain, result):
        if info['kind'] != 'vault': raise StorageError('recovery requires a vault backup')
        store = VaultStore()
        with store.locked():
            if not store.path.exists():
                if any((store.directory/name).exists() for name in ('vault.db','salt','verify')):
                    raise StorageError('legacy vault exists; preserve or migrate it before recovery')
                stage = store._stage()
                try:
                    shutil.copyfile(plain, stage); stage.chmod(0o600)
                    store._publish(stage)
                finally: stage.unlink(missing_ok=True)
                return {'activated': identifier, 'previous_vault': None, 'checks': result}
            if current_password is None: raise StorageError('current vault password required before replacement')
            store._require_v2()
            # Keep the same vault DB inode and lock: replace rows in one transaction.
            active = _connect(store.path, writable=True)
            source = _connect(plain)
            preserved = None
            try:
                _validate_records(active, unlock_connection(active, current_password))
                retained = private_dir(Path.home()/'.ish-toolkit/recovery') / ('before-' + uuid.uuid4().hex)
                retained.mkdir(mode=0o700)
                preserved = retained/'vault-v2.db'
                fd = os.open(preserved, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600); os.close(fd)
                target = sqlite3.connect(preserved)
                try: active.backup(target)
                finally: target.close()
                from .vault_store import inspect_snapshot
                inspect_snapshot(preserved, current_password)
                sync_file(preserved); sync_dir(retained); sync_dir(retained.parent)
                _checkpoint('recovery_preserved')
                active.execute('BEGIN IMMEDIATE')
                # Source is a private authenticated copy held by verified_copy.
                for table in ('secrets', 'totp', 'vault_meta'):
                    active.execute(f'DELETE FROM {table}')
                    for row in source.execute(f'SELECT * FROM {table}'):
                        active.execute(f'INSERT INTO {table} VALUES ({",".join("?" for _ in row)})', row)
                    _checkpoint('recovery_replaced_table')
                _validate_records(active, unlock_connection(active, snapshot_password))
                _checkpoint('before_commit')
                active.commit()
                _checkpoint('after_commit')
                return {'activated': identifier, 'previous_vault': str(retained), 'checks': result}
            except BaseException:
                active.rollback(); raise
            finally:
                source.close(); active.close()
