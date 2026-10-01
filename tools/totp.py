#!/usr/bin/env python3
import os, sys, time, sqlite3, getpass
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import hash_secret_raw, Type
import pyotp

VDIR = Path.home() / ".vault"
VDB  = VDIR / "vault.db"
SALT = VDIR / "salt"
VER  = VDIR / "verify"

def derive(pw, s):
    return hash_secret_raw(secret=pw.encode(), salt=s,
        time_cost=3, memory_cost=65536, parallelism=1,
        hash_len=32, type=Type.ID)

def unlock():
    if not SALT.exists(): print("run: vault init"); sys.exit(1)
    p = getpass.getpass("Master password: ")
    k = derive(p, SALT.read_bytes())
    b = VER.read_bytes()
    try: AESGCM(k).decrypt(b[:12], b[12:], None)
    except: print("wrong password"); sys.exit(1)
    return k

def tbl():
    VDIR.mkdir(mode=0o700, exist_ok=True)
    c = sqlite3.connect(VDB)
    c.execute("CREATE TABLE IF NOT EXISTS totp (name TEXT PRIMARY KEY, blob BLOB)")
    c.commit()
    return c

def add(name, secret=None):
    k = unlock()
    if secret is None:
        secret = getpass.getpass("Secret (base32): ").strip().replace(" ", "").upper()
    try: pyotp.TOTP(secret).now()
    except: print("invalid"); sys.exit(1)
    n = os.urandom(12)
    ct = AESGCM(k).encrypt(n, secret.encode(), name.encode())
    c = tbl()
    c.execute("INSERT OR REPLACE INTO totp VALUES (?, ?)", (name, n + ct))
    c.commit(); c.close()
    print(f"added: {name}")

def show(name=None):
    k = unlock()
    c = tbl()
    if name:
        r = c.execute("SELECT name, blob FROM totp WHERE name=?", (name,)).fetchall()
    else:
        r = c.execute("SELECT name, blob FROM totp ORDER BY name").fetchall()
    c.close()
    if not r: print("no entries"); return
    now = int(time.time())
    for n, b in r:
        try:
            s = AESGCM(k).decrypt(b[:12], b[12:], n.encode()).decode()
            code = pyotp.TOTP(s).now()
            rem = 30 - (now % 30)
            bar = "#" * (rem // 3) + "." * (10 - rem // 3)
            print(f"{n:20} {code}  [{bar}] {rem:2}s")
        except Exception as e:
            print(f"{n:20} ERROR {e}")

def ls():
    c = tbl()
    r = c.execute("SELECT name FROM totp ORDER BY name").fetchall()
    c.close()
    if not r: print("(empty)"); return
    for (n,) in r: print(n)

def rm(n):
    unlock()
    c = tbl()
    c.execute("DELETE FROM totp WHERE name=?", (n,))
    c.commit(); c.close()
    print(f"deleted: {n}")

def usage():
    print("totp add <n> [secret] | <n> | | list | delete <n>")

def main():
    if len(sys.argv) == 1: show(); return
    c = sys.argv[1]
    if c == "add" and len(sys.argv) >= 3:
        add(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif c == "list": ls()
    elif c == "delete" and len(sys.argv) == 3: rm(sys.argv[2])
    elif c.startswith("-"): usage()
    else: show(c)

if __name__ == "__main__": main()
