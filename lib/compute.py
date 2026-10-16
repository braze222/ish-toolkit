#!/usr/bin/env python3
"""Compatibility facade for the unified compute CLI (no duplicate provider state)."""
import sys
from .orchestration.cli import main as control_main

def local(): return control_main(['compute','local'])
def docker(): return control_main(['compute','docker'])
def remote(): return control_main(['compute','remote'])
def colab(): return control_main(['compute','colab'])
def status(): return control_main(['compute','status'])
def main(): return control_main(['compute', *sys.argv[1:]])

if __name__ == '__main__':
    raise SystemExit(main())
