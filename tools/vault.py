#!/usr/bin/env python3
import os, sys, sqlite3, getpass
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import hash_secret_raw, Type

VDIR = Path.home() / ".vault"
VDB  = VDIR / "vault.db"
SALT = VDIR / "salt"
VER  = VDIR / "verify"

def ensure(): VDIR.mkdir(mode=0o700, exist_ok=True)
def derive(pw, s):
    return hash_secret_raw(secret=pw.encode(), salt=s,
        time_cost=3, memory_cost=65536, parallelism=1,
        hash_len=32, type=Type.ID)

def init():
    ensure()
    if SALT.exists(): print("already initialized"); return
    p1 = getpass.getpass("Master password: ")
    p2 = getpass.getpass("Confirm: ")
    if p1 != p2: print("mismatch"); sys.exit(1)
    if len(p1) < 8: print("need 8+ chars"); sys.exit(1)
    salt = os.urandom(16)
    SALT.write_bytes(salt); SALT.chmod(0o600)
    key = derive(p1, salt)
    n = os.urandom(12)
    ct = AESGCM(key).encrypt(n, b"verify", None)
    VER.write_bytes(n + ct); VER.chmod(0o600)
    c = sqlite3.connect(VDB)
    c.execute("CREATE TABLE IF NOT EXISTS secrets (key TEXT PRIMARY KEY, blob BLOB)")
    c.commit(); c.close()
    VDB.chmod(0o600)
    print("vault initialized")

def unlock():
    if not SALT.exists(): print("run: vault init"); sys.exit(1)
    p = getpass.getpass("Master password: ")
    k = derive(p, SALT.read_bytes())
    b = VER.read_bytes()
    try: AESGCM(k).decrypt(b[:12], b[12:], None)
    except: print("wrong password"); sys.exit(1)
    return k

def set_s(n):
    k = unlock()
    v = getpass.getpass(f"Value for {n}: ")
    nonce = os.urandom(12)
    ct = AESGCM(k).encrypt(nonce, v.encode(), n.encode())
    c = sqlite3.connect(VDB)
    c.execute("INSERT OR REPLACE INTO secrets VALUES (?, ?)", (n, nonce + ct))
    c.commit(); c.close()
    print(f"stored: {n}")

def get_s(n):
    k = unlock()
    c = sqlite3.connect(VDB)
    r = c.execute("SELECT blob FROM secrets WHERE key=?", (n,)).fetchone()
    c.close()
    if not r: print("not found"); sys.exit(1)
    b = r[0]
    print(AESGCM(k).decrypt(b[:12], b[12:], n.encode()).decode())

def ls():
    if not VDB.exists(): print("no vault"); sys.exit(1)
    c = sqlite3.connect(VDB)
    r = c.execute("SELECT key FROM secrets ORDER BY key").fetchall()
    c.close()
    if not r: print("(empty)"); return
    for (k,) in r: print(k)

def rm(n):
    unlock()
    c = sqlite3.connect(VDB)
    c.execute("DELETE FROM secrets WHERE key=?", (n,))
    c.commit(); c.close()
    print(f"deleted: {n}")

def usage():
    print("vault init | set <n> | get <n> | list | delete <n>")

def main():
    if len(sys.argv) < 2: usage(); return
    c = sys.argv[1]
    if c == "init": init()
    elif c == "set" and len(sys.argv) == 3: set_s(sys.argv[2])
    elif c == "get" and len(sys.argv) == 3: get_s(sys.argv[2])
    elif c == "list": ls()
    elif c == "delete" and len(sys.argv) == 3: rm(sys.argv[2])
    else: usage()

if __name__ == "__main__": main()
