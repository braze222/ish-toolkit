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
import stat

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ('ish', 'ish-db', 'ish-doctor', 'ish-compute', 'ish-workspace', 'ish-backup', 'ish-selftest', 'ish-verify', 'vault', 'totp', 'crypt', 'shred')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('full', 'control'), default='full', help='control installs stdlib compute tools only; full also requires crypto dependencies')
    parser.add_argument('--bin-dir', type=Path, default=Path.home() / '.local' / 'bin')
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error('Python 3.10 or newer is required')
    modules = ['sqlite3', 'fcntl']
    if args.profile == 'full':
        modules += ['cryptography.hazmat.primitives.ciphers.aead', 'argon2.low_level', 'pyotp']
    tools = TOOLS + ('ish-compatibility',) if args.profile == 'full' else ('ish', 'ish-compute', 'ish-compatibility', 'ish-verify')
    for module in modules:
        try:
            importlib.import_module(module)
        except ImportError:
            parser.error(f'Missing {module}. Activate your existing toolkit venv or see docs/python.md.')
    for directory in ('lib', 'tools'):
        for path in (ROOT / directory).rglob('*.py'):
            compile(path.read_text(), str(path), 'exec')
    for name in tools:
        source = ROOT / 'tools' / (name + '.py')
        if source.is_symlink() or not source.is_file():
            parser.error(f'Missing or unsafe tool source: {name}')
    bindir = args.bin_dir.expanduser().absolute()
    bindir.mkdir(parents=True, exist_ok=True)
    for name in tools:
        target = bindir / name
        if target.exists() and not target.is_symlink() and not stat.S_ISREG(target.lstat().st_mode):
            parser.error(f'Cannot replace non-regular launcher: {target}')
    backup = Path(tempfile.mkdtemp(prefix='ish-toolkit-install-backup-', dir=bindir))
    originals = {}
    replaced = []
    try:
        for name in tools:
            target = bindir / name
            existed = target.exists() or target.is_symlink()
            saved = backup / name
            if existed:
                if target.is_symlink():
                    originals[name] = ('symlink', os.readlink(target))
                    os.symlink(originals[name][1], saved)
                else:
                    originals[name] = ('file', None)
                    shutil.copy2(target, saved, follow_symlinks=False)
            else:
                originals[name] = ('absent', None)

            content = ('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' +
                       shlex.quote(str(ROOT / 'tools' / (name + '.py'))) + ' "$@"\n')
            fd, temp = tempfile.mkstemp(prefix='.ish-install-', dir=bindir)
            try:
                with os.fdopen(fd, 'w') as handle:
                    handle.write(content)
                os.chmod(temp, 0o700)
                # Track before replacement so rollback covers a failure
                # immediately after the filesystem operation.
                replaced.append(name)
                os.replace(temp, target)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
    except (Exception, KeyboardInterrupt) as install_error:
        rollback_errors = []
        for name in reversed(replaced):
            target = bindir / name
            kind, link_target = originals[name]
            try:
                if target.exists() or target.is_symlink():
                    if target.is_dir() and not target.is_symlink():
                        raise IsADirectoryError(str(target))
                    target.unlink()
                if kind == 'symlink':
                    os.symlink(link_target, target)
                elif kind == 'file':
                    shutil.copy2(backup / name, target, follow_symlinks=False)
            except Exception as rollback_error:
                rollback_errors.append(f'{name}: {rollback_error}')
        if rollback_errors:
            raise RuntimeError(
                f'Installation failed: {install_error}; rollback also failed: '
                + '; '.join(rollback_errors)
                + f'; recovery backups retained at {backup}'
            ) from install_error
        raise
    import platform
    print(f'Platform: {platform.system()} {platform.machine()} {platform.release()}')
    print(f'Installed local toolkit from {ROOT}')
    print(f'Previous launchers saved in {backup}')
    print('Keep this source folder in place; launchers refer to it.')
    print('Run: export PATH="$HOME/.local/bin:$PATH"')
    print('Profile: ' + args.profile)
    print('Then: ish selftest --full' if args.profile == 'full' else 'Then: ish compatibility; ish selftest --control')
    print('Existing v2 vault: run ish vault verify; no migration or initialization needed.')
    print('Legacy vault only: stop old clients, preserve data, then run ish vault migrate.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
