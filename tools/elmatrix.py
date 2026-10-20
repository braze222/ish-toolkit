#!/usr/bin/env python3
"""Separate research entry point. Does not change the ish dispatcher."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.elmatrix.cli import main
if __name__ == '__main__':
    raise SystemExit(main())
