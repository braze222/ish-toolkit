#!/usr/bin/env python3
"""Isolated compatibility checks; all state lives under a temporary HOME."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.storage import lock, StorageError, sync_dir, publish_new
from lib import workspaces, backups, transfer, recovery, keys
from lib.db import SQLiteDB
from lib.db_policy import DBPolicy
from lib.vault_store import VaultStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true', help='Also exercise Argon2, vault rotation and encrypted vault recovery; slower on iSH')
    args = parser.parse_args(argv)
    old_home = os.environ.get('HOME')
    try:
        with tempfile.TemporaryDirectory(prefix='ish-selftest-') as directory:
            os.environ['HOME'] = directory
            base = Path(directory)
            print('Checking locks, durable writes and exclusive publication...', flush=True)
            with lock(base / 'test.lock'):
                try:
                    with lock(base / 'test.lock'): raise RuntimeError('lock allowed concurrent access')
                except StorageError: pass
            staged = base / 'stage'; staged.write_text('test')
            publish_new(staged, base / 'published')
            sync_dir(base)
            print('PASS: filesystem primitives', flush=True)
            info = workspaces.create('selftest')
            path = workspaces.resolve_database('@selftest')
            with SQLiteDB(path, DBPolicy(False, True)) as db:
                db.execute('CREATE TABLE sample(value TEXT)')
                db.execute('INSERT INTO sample VALUES (?)', ('expected',))
            snapshot = backups.create('@selftest')
            backups.verify(snapshot['id'])
            destination = base / 'restored.db'
            backups.restore(snapshot['id'], destination)
            with SQLiteDB(destination) as db:
                if db.query('SELECT * FROM sample') != [{'value': 'expected'}]:
                    raise RuntimeError('restored contents differ')
                try: db.execute('DELETE FROM sample')
                except Exception: pass
                else: raise RuntimeError('read-only write permitted')
            bundle = base / 'selftest.ishbackup'
            transfer.export_bundle(snapshot['id'], bundle)
            import shutil
            shutil.rmtree(backups.root() / snapshot['id'])
            transfer.import_bundle(bundle)
            print('PASS: workspace, SQLite policy, backup export/import and restore', flush=True)
            from lib.orchestration import engine
            job = engine.submit({'command': [sys.executable, '-c',
                'from pathlib import Path; print("compute-selftest"); Path("result.txt").write_text("expected")'],
                'backend': 'local', 'timeout': 30, 'outputs': ['result.txt']}, execute=True)
            if job['state'] != 'completed':
                raise RuntimeError('local compute execution failed or unknown')
            if 'compute-selftest' not in engine.logs(job['id'])['text']:
                raise RuntimeError('compute log retrieval failed')
            engine.artifacts(job['id'], base / 'compute-result')
            if (base / 'compute-result/result.txt').read_text() != 'expected':
                raise RuntimeError('compute artifact round trip failed')
            print('PASS: isolated local compute job, logs and artifact retrieval (no remote accounts used)', flush=True)
            if args.full:
                print('Testing vault encryption and transactional rotation (may take time on iSH)...', flush=True)
                vault = VaultStore()
                old, new = 'Temporary-selftest-old!', 'Temporary-selftest-new!'
                vault.initialize(old)
                vault.put('sample', 'expected-secret', old)
                vault.put('sample-2fa', 'JBSWY3DPEHPK3PXP', old, 'totp')
                vault.rotate(old, new)
                if vault.get('sample', new) != 'expected-secret': raise RuntimeError('vault round trip failed')
                from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
                from cryptography.hazmat.primitives import serialization
                key_directory = base / '.crypt'; key_directory.mkdir(mode=0o700)
                key = key_directory / 'id.key'
                key.write_bytes(X25519PrivateKey.generate().private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
                key.chmod(0o600)
                snapshot = backups.create('vault', encrypted=True, password=new)
                backups.verify(snapshot['id'], new)
                recovered = base / 'recovered-vault'
                backups.restore(snapshot['id'], recovered, new)
                if VaultStore(recovered).get('sample', new) != 'expected-secret': raise RuntimeError('vault recovery failed')
                vault.put('sample', 'changed-after-backup', new)
                activated = recovery.recover(snapshot['id'], new, new)
                if vault.get('sample', new) != 'expected-secret': raise RuntimeError('activation failed')
                if VaultStore(activated['previous_vault']).get('sample', new) != 'changed-after-backup': raise RuntimeError('recovery copy failed')
                keys.protect('Temporary-crypt-password!')
                keys.load(password='Temporary-crypt-password!')
                print('PASS: vault rotation, streaming encrypted backup, activation and protected key', flush=True)
            else:
                print('Vault crypto was not exercised. Run ish selftest --full for those checks.', flush=True)
        print('PASS: selected self-tests completed; live user data was not used.', flush=True)
        return 0
    except Exception as exc:
        print(f'FAIL: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    finally:
        if old_home is None: os.environ.pop('HOME', None)
        else: os.environ['HOME'] = old_home


if __name__ == '__main__': raise SystemExit(main())
