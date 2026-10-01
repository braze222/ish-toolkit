#!/usr/bin/env python3
import os, sys, tarfile, tempfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey, X25519PublicKey)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KDIR = Path.home() / ".crypt"
PRIV = KDIR / "id.key"
PUB  = KDIR / "id.pub"
MAGIC = b"CRYPTv1\x00"

def ensure(): KDIR.mkdir(mode=0o700, exist_ok=True)

def keygen():
    ensure()
    if PRIV.exists(): print("exists"); return
    p = X25519PrivateKey.generate()
    PRIV.write_bytes(p.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()))
    PRIV.chmod(0o600)
    PUB.write_bytes(p.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw))
    PUB.chmod(0o644)
    print("keypair generated")

def lpriv():
    if not PRIV.exists(): print("run: crypt keygen"); sys.exit(1)
    return X25519PrivateKey.from_private_bytes(PRIV.read_bytes())

def lpub(p):
    return X25519PublicKey.from_public_bytes(Path(p).read_bytes())

def derive(s, salt):
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt,
                info=b"crypt-v1").derive(s)

def enc(inp, out=None, recip=None):
    inp = Path(inp)
    if not inp.exists(): print("no file"); sys.exit(1)
    out = Path(out) if out else Path(str(inp) + ".crypt")
    tgt = lpub(recip) if recip else lpriv().public_key()
    e = X25519PrivateKey.generate()
    shared = e.exchange(tgt)
    salt = os.urandom(16)
    key = derive(shared, salt)
    nonce = os.urandom(12)
    ep = e.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)
    data = inp.read_bytes()
    ct = ChaCha20Poly1305(key).encrypt(nonce, data, None)
    out.write_bytes(MAGIC + salt + ep + nonce + ct)
    out.chmod(0o600)
    print(f"enc: {inp} -> {out}")

def dec(inp, out=None):
    inp = Path(inp)
    if not inp.exists(): print("no file"); sys.exit(1)
    if out: out = Path(out)
    else:
        s = str(inp)
        out = Path(s[:-6] if s.endswith(".crypt") else s + ".dec")
    blob = inp.read_bytes()
    if not blob.startswith(MAGIC): print("not crypt format"); sys.exit(1)
    o = len(MAGIC)
    salt = blob[o:o+16]; o += 16
    ep = blob[o:o+32]; o += 32
    nonce = blob[o:o+12]; o += 12
    ct = blob[o:]
    shared = lpriv().exchange(X25519PublicKey.from_public_bytes(ep))
    key = derive(shared, salt)
    try:
        pt = ChaCha20Poly1305(key).decrypt(nonce, ct, None)
    except: print("decrypt failed"); sys.exit(1)
    out.write_bytes(pt)
    print(f"dec: {inp} -> {out}")

def encdir(inp):
    inp = Path(inp)
    if not inp.is_dir(): print("not a dir"); sys.exit(1)
    tmp = Path(tempfile.mktemp(suffix=".tar"))
    with tarfile.open(tmp, "w") as t:
        t.add(inp, arcname=inp.name)
    enc(tmp, Path(str(inp) + ".tar.crypt"))
    tmp.unlink()

def usage():
    print("crypt keygen | pubkey | encrypt <f> | encrypt -r <pub> <f> | encrypt-dir <d> | decrypt <f>")

def main():
    if len(sys.argv) < 2: usage(); return
    c = sys.argv[1]
    if c == "keygen": keygen()
    elif c == "pubkey":
        if not PUB.exists(): print("no key"); sys.exit(1)
        print(PUB.read_bytes().hex())
    elif c == "encrypt":
        if len(sys.argv) >= 4 and sys.argv[2] == "-r":
            enc(sys.argv[4], None, sys.argv[3])
        elif len(sys.argv) == 3: enc(sys.argv[2])
        elif len(sys.argv) == 4: enc(sys.argv[2], sys.argv[3])
        else: usage()
    elif c == "encrypt-dir" and len(sys.argv) == 3: encdir(sys.argv[2])
    elif c == "decrypt" and len(sys.argv) >= 3:
        dec(sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None)
    else: usage()

if __name__ == "__main__": main()
