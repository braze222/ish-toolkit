"""Streaming CRYPTv2 AES-256-GCM; read-compatible with bounded CRYPTv1."""
import os
from pathlib import Path
import tempfile
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import serialization, hashes
from .storage import StorageError, publish_new
from . import keys

MAGIC = b'CRYPTv2\x00'
LEGACY = b'CRYPTv1\x00'
CHUNK = 1024 * 1024
LIMIT = 60 * 1024**3  # Below the per-message GCM bound; not an unlimited format.
LEGACY_LIMIT = 32 * 1024**2


def private_key():
    return keys.load()


def _derive(shared, salt, info=b'crypt-v2'):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=info).derive(shared)


def encrypt_file(source, target, recipient=None):
    source, target = Path(source), Path(target)
    if target.exists() or target.is_symlink(): raise FileExistsError(target)
    recipient = recipient or private_key().public_key()
    ephemeral = X25519PrivateKey.generate()
    salt, nonce = os.urandom(16), os.urandom(12)
    key = _derive(ephemeral.exchange(recipient), salt)
    public = ephemeral.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    header = MAGIC + salt + public + nonce
    enc = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    enc.authenticate_additional_data(header)
    with tempfile.TemporaryDirectory(prefix='.crypt-', dir=target.parent) as folder:
        staged = Path(folder) / 'output'
        with source.open('rb') as inp, staged.open('xb') as out:
            staged.chmod(0o600)
            out.write(header)
            total = 0
            for block in iter(lambda: inp.read(CHUNK), b''):
                total += len(block)
                if total > LIMIT: raise StorageError('stream exceeds 60 GiB supported size')
                out.write(enc.update(block))
            out.write(enc.finalize()); out.write(enc.tag)
            out.flush(); os.fsync(out.fileno())
        publish_new(staged, target)


def decrypt_file(source, target, key=None):
    source, target = Path(source), Path(target)
    if target.exists() or target.is_symlink(): raise FileExistsError(target)
    key = key or private_key()
    try:
        with source.open('rb') as inp, tempfile.TemporaryDirectory(prefix='.crypt-', dir=target.parent) as folder:
            staged = Path(folder) / 'output'
            header = inp.read(68)
            if len(header) != 68: raise StorageError('invalid encrypted backup format')
            shared = key.exchange(X25519PublicKey.from_public_bytes(header[24:56]))
            with staged.open('xb') as out:
                staged.chmod(0o600)
                if header[:8] == LEGACY:
                    blob = inp.read(LEGACY_LIMIT + 17)
                    if len(blob) > LEGACY_LIMIT + 16: raise StorageError('legacy encrypted file exceeds 32 MiB; use the old crypt client for larger legacy files')
                    value = ChaCha20Poly1305(_derive(shared, header[8:24], b'crypt-v1')).decrypt(header[56:68], blob, None)
                    out.write(value)
                elif header[:8] == MAGIC:
                    dec = Cipher(algorithms.AES(_derive(shared, header[8:24])), modes.GCM(header[56:68])).decryptor()
                    dec.authenticate_additional_data(header)
                    pending = b''; total = 0
                    for block in iter(lambda: inp.read(CHUNK), b''):
                        pending += block
                        if len(pending) > 16:
                            part, pending = pending[:-16], pending[-16:]
                            total += len(part)
                            if total > LIMIT: raise StorageError('stream exceeds supported size')
                            out.write(dec.update(part))
                    if len(pending) != 16: raise StorageError('truncated authentication tag')
                    out.write(dec.finalize_with_tag(pending))
                else:
                    raise StorageError('invalid encrypted backup format')
                out.flush(); os.fsync(out.fileno())
            # No plaintext is published until the entire stream authenticates.
            publish_new(staged, target)
    except (InvalidTag, ValueError) as exc:
        raise StorageError('backup decryption failed: wrong key or damaged file') from exc
