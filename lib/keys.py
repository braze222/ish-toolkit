"""Raw legacy and password-protected PKCS8 X25519 keys."""
import getpass
import os
from pathlib import Path
import tempfile
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from .storage import regular_file, private_dir, lock, sync_dir, StorageError


def load(path=None, password=None):
    path = regular_file(path or Path.home() / '.crypt/id.key')
    if path.stat().st_mode & 0o077:
        raise StorageError('crypt private key permissions must be 0600')
    data = path.read_bytes()
    try:
        if len(data) == 32:
            return X25519PrivateKey.from_private_bytes(data)
        if not data.startswith(b'-----BEGIN ENCRYPTED PRIVATE KEY-----'):
            raise ValueError('unsupported key')
        if password is None:
            password = getpass.getpass('Crypt key password: ')
        key = serialization.load_pem_private_key(data, password.encode())
        if not isinstance(key, X25519PrivateKey): raise ValueError('wrong key type')
        return key
    except (ValueError, TypeError) as exc:
        raise StorageError('cannot unlock crypt key: wrong password or invalid key') from exc


def protect(new_password, old_password=None, path=None):
    """Atomically replace key encoding, preserving its cryptographic identity."""
    if len(new_password) < 12:
        raise StorageError('key password must contain at least 12 characters')
    path = Path(path or Path.home() / '.crypt/id.key')
    private_dir(path.parent)
    with lock(path.parent / '.key.lock'):
        key = load(path, old_password)
        encoded = key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(new_password.encode()))
        check = serialization.load_pem_private_key(encoded, new_password.encode())
        raw = lambda k: k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if raw(key) != raw(check): raise StorageError('key verification failed')
        fd, name = tempfile.mkstemp(prefix='.protected-key-', dir=path.parent)
        staged = Path(name)
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(encoded); handle.flush(); os.fsync(handle.fileno())
            os.replace(staged, path)
            sync_dir(path.parent)
        finally:
            staged.unlink(missing_ok=True)
    return {'protected': True, 'key_identity': 'unchanged', 'path': str(path)}
