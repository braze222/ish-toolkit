#!/usr/bin/env python3
"""Install wrappers for this source tree without copying over user code/data."""
import argparse
import importlib
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ('ish', 'ish-db', 'ish-doctor', 'ish-compute', 'ish-workspace', 'ish-backup', 'ish-selftest', 'vault', 'totp', 'crypt', 'shred')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir', type=Path, default=Path.home() / '.local' / 'bin')
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error('Python 3.10 or newer is required')
    for module in ('sqlite3', 'fcntl', 'cryptography.hazmat.primitives.ciphers.aead', 'argon2.low_level', 'pyotp'):
        try:
            importlib.import_module(module)
        except ImportError:
            parser.error(f'Missing {module}. Activate your existing toolkit venv or see docs/python.md.')
    for directory in ('lib', 'tools'):
        for path in (ROOT / directory).rglob('*.py'):
            compile(path.read_text(), str(path), 'exec')
    bindir = args.bin_dir.expanduser().absolute()
    bindir.mkdir(parents=True, exist_ok=True)
    for name in TOOLS:
        target = bindir / name
        if target.is_dir() and not target.is_symlink():
            parser.error(f'Cannot replace directory: {target}')
    backup = Path(tempfile.mkdtemp(prefix='ish-toolkit-install-backup-', dir=bindir))
    installed = []
    try:
        for name in TOOLS:
            target = bindir / name
            if target.exists() or target.is_symlink():
                shutil.copy2(target, backup / name, follow_symlinks=False)
            content = ('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' +
                       shlex.quote(str(ROOT / 'tools' / (name + '.py'))) + ' "$@"\n')
            fd, temp = tempfile.mkstemp(prefix='.ish-install-', dir=bindir)
            try:
                with os.fdopen(fd, 'w') as handle:
                    handle.write(content)
                os.chmod(temp, 0o700)
                os.replace(temp, target)
                installed.append(name)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
    except Exception:
        for name in installed:
            target = bindir / name
            target.unlink()
            saved = backup / name
            if saved.exists() or saved.is_symlink():
                shutil.copy2(saved, target, follow_symlinks=False)
        raise
    import platform
    print(f'Platform: {platform.system()} {platform.machine()} {platform.release()}')
    print(f'Installed local toolkit from {ROOT}')
    print(f'Previous launchers saved in {backup}')
    print('Keep this source folder in place; launchers refer to it.')
    print('Run: export PATH="$HOME/.local/bin:$PATH"')
    print('Then: ish selftest --full')
    print('Existing v2 vault: run ish vault verify; no migration or initialization needed.')
    print('Legacy vault only: stop old clients, preserve data, then run ish vault migrate.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
