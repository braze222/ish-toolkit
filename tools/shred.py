#!/usr/bin/env python3
import os, sys
from pathlib import Path

PASSES = 3

def shred_file(p):
    p = Path(p)
    if not p.is_file():
        print("not file: " + str(p))
        return
    size = p.stat().st_size
    try:
        with open(p, "r+b") as f:
            for _ in range(PASSES):
                f.seek(0)
                f.write(os.urandom(size))
                f.flush()
                os.fsync(f.fileno())
        tmp = p.with_suffix(p.suffix + ".s")
        p.rename(tmp)
        tmp.unlink()
        print("shredded: " + str(p))
    except Exception as e:
        print("error: " + str(e))

def shred_dir(p):
    p = Path(p)
    if not p.is_dir():
        print("not dir")
        return
    for f in sorted(p.rglob("*"), reverse=True):
        if f.is_file():
            shred_file(f)
        elif f.is_dir():
            try:
                f.rmdir()
            except OSError:
                pass
    try:
        p.rmdir()
    except OSError:
        pass
    print("shredded dir: " + str(p))

def usage():
    print("shred <file> | shred -r <folder>")

def main():
    if len(sys.argv) < 2:
        usage()
        return
    if sys.argv[1] == "-r" and len(sys.argv) == 3:
        shred_dir(sys.argv[2])
    elif len(sys.argv) == 2:
        shred_file(sys.argv[1])
    else:
        usage()

if __name__ == "__main__":
    main()
