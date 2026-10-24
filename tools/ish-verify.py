#!/usr/bin/env python3
"""Fast control verification, with an explicit full-test mode."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true",
                      help="syntax and isolated control self-test (default)")
    mode.add_argument("--full", action="store_true",
                      help="run all unit tests and Elmatrix verification")
    args = parser.parse_args()

    os.chdir(ROOT)
    results = []

    def check(name, command, cwd=ROOT):
        print(f"\n[RUN ] {name}", flush=True)
        try:
            result = subprocess.run(command, cwd=cwd, check=False, timeout=900)
            passed = result.returncode == 0
            if not passed:
                print(f"       Exit code: {result.returncode}")
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"       Could not run: {exc}")
            passed = False
        results.append((name, passed))
        print(f"[{'PASS' if passed else 'FAIL'}] {name}", flush=True)

    print("ISH TOOLKIT VERIFICATION")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Root:   {ROOT}")
    print(f"Mode:   {'full' if args.full else 'quick'}")

    print("\n[RUN ] Python syntax", flush=True)
    errors = []
    for directory in ("lib", "tools", "tests", "scripts", "elmatrix-standalone/elmatrix", "elmatrix-standalone/tests"):
        base = ROOT / directory
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except (SyntaxError, UnicodeError, OSError) as exc:
                errors.append(f"{path.relative_to(ROOT)}: {exc}")
    for error in errors:
        print(f"       {error}")
    results.append(("Python syntax", not errors))
    print(f"[{'FAIL' if errors else 'PASS'}] Python syntax")

    if args.full:
        try:
            import pytest  # noqa: F401
        except ImportError:
            print("\n[SKIP] Full unit tests: pytest is not installed.")
            print("       Install development dependencies in an appropriate environment:")
            print("       python3 -m pip install -r requirements-dev.txt")
            results.append(("Full unit tests (pytest required)", False))
        else:
            check(
                "Toolkit unit tests",
                [sys.executable, "-m", "pytest", "-q", "tests"],
            )

        elmatrix = ROOT / "elmatrix-standalone"
        verifier = elmatrix / "scripts" / "ish-verify"
        if verifier.is_file():
            check(
                "Elmatrix standalone verification",
                [sys.executable, str(verifier)],
                cwd=elmatrix,
            )
        else:
            print("\n[FAIL] Elmatrix standalone verifier missing")
            results.append(("Elmatrix standalone verifier missing", False))

    check(
        "Isolated full self-test" if args.full else "Isolated control self-test (artifacts omitted)",
        [sys.executable, str(ROOT / "tools" / "ish-selftest.py"), "--full"] if args.full else
        [sys.executable, str(ROOT / "tools" / "ish-selftest.py"), "--control", "--skip-artifacts"],
    )

    print("\n=== VERIFICATION SUMMARY ===")
    for name, passed in results:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    failed = [name for name, passed in results if not passed]
    print(f"\nPassed: {len(results) - len(failed)} / {len(results)} checks")
    if failed:
        print("Verification FAILED: " + ", ".join(failed))
        return 1
    print("Verification PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
