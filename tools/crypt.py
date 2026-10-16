#!/usr/bin/env python3
import os, sys, tarfile, tempfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey, X25519PublicKey)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import keys, backup_crypto
from lib.storage import StorageError
import getpass

KDIR = Path.home() / ".crypt"
PRIV = KDIR / "id.key"
PUB  = KDIR / "id.pub"
MAGIC = b"CRYPTv1\x00"

def ensure(): KDIR.mkdir(mode=0o700, exist_ok=True)

def keygen():
    created = keys.create(KDIR)
    print('keypair generated; run ish crypt protect-key to add a password' if created else 'exists; private key preserved')

def lpriv():
    if not PRIV.exists(): print("run: crypt keygen"); sys.exit(1)
    return keys.load(PRIV)

def lpub(p):
    return X25519PublicKey.from_public_bytes(Path(p).read_bytes())

def derive(s, salt):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt,
                info=b"crypt-v1").derive(s)

def enc(inp, out=None, recip=None):
    inp = Path(inp)
    if not inp.exists(): print("no file"); sys.exit(1)
    out = Path(out) if out else Path(str(inp) + ".crypt")
    backup_crypto.encrypt_file(inp, out, lpub(recip) if recip else lpriv().public_key())
    print(f"enc: {inp} -> {out}")

def dec(inp, out=None):
    inp = Path(inp)
    out = Path(out) if out else Path(str(inp)[:-6] if str(inp).endswith('.crypt') else str(inp) + '.dec')
    try:
        backup_crypto.decrypt_file(inp, out, lpriv())
    except StorageError as exc:
        print(str(exc)); raise SystemExit(1)
    print(f"dec: {inp} -> {out}")


def encdir(inp):
    inp = Path(inp)
    if not inp.is_dir(): print("not a dir"); sys.exit(1)
    with tempfile.TemporaryDirectory(prefix="ish-crypt-") as directory:
        tmp = Path(directory) / "input.tar"
        with tarfile.open(tmp, "w") as t:
            t.add(inp, arcname=inp.name)
        enc(tmp, Path(str(inp) + ".tar.crypt"))

def usage():
    print("crypt keygen | protect-key | key-status | pubkey | encrypt <f> | encrypt -r <pub> <f> | encrypt-dir <d> | decrypt <f>")

def main():
    if len(sys.argv) < 2: usage(); return
    c = sys.argv[1]
    if c == "keygen": keygen()
    elif c == "protect-key":
        first = getpass.getpass('New crypt key password (12+ characters): ')
        if first != getpass.getpass('Confirm new key password: '):
            raise StorageError('password confirmation does not match')
        keys.protect(first, path=PRIV)
        print('Key protected; key identity unchanged. Back up the protected id.key file.')
    elif c == "key-status":
        data = PRIV.read_bytes()
        print('password-protected' if data.startswith(b'-----BEGIN ENCRYPTED PRIVATE KEY-----') else 'legacy raw key' if len(data) == 32 else 'unknown key format')
    elif c == "pubkey":
        if not PUB.exists(): print("no key"); sys.exit(1)
        print(PUB.read_bytes().hex())
    elif c == "encrypt":
        if len(sys.argv) == 5 and sys.argv[2] == "-r":
            enc(sys.argv[4], None, sys.argv[3])
        elif len(sys.argv) == 3: enc(sys.argv[2])
        elif len(sys.argv) == 4: enc(sys.argv[2], sys.argv[3])
        else: usage()
    elif c == "encrypt-dir" and len(sys.argv) == 3: encdir(sys.argv[2])
    elif c == "decrypt" and len(sys.argv) >= 3:
        dec(sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None)
    else: usage()

if __name__ == "__main__":
    try: main()
    except (StorageError, OSError) as exc:
        print(f'crypt: {exc}', file=sys.stderr); raise SystemExit(1)
    except (KeyboardInterrupt, EOFError): raise SystemExit(130)
