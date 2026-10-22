#!/usr/bin/env python3
"""Build and optionally install a standalone Elmatrix zipapp, with atomic replacement."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipapp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.storage import lock, private_dir, regular_file, sync_dir, sync_file


def build(output):
    output = private_dir(output)
    with lock(output / '.build.lock'):
        return _build_locked(output)


def _build_locked(output):
    with tempfile.TemporaryDirectory(prefix='elmatrix-build-') as tmp:
        staging = Path(tmp)
        (staging / 'lib' / 'elmatrix').mkdir(parents=True)
        for relative in ('lib/__init__.py', 'lib/storage.py', 'lib/elmatrix/__init__.py', 'lib/elmatrix/cli.py'):
            target = staging / relative
            target.write_bytes((ROOT / relative).read_bytes())
        (staging / '__main__.py').write_text('import sys\nif sys.version_info < (3, 10):\n    sys.exit("Elmatrix requires Python 3.10+")\nfrom lib.elmatrix.cli import main\nraise SystemExit(main())\n')
        archive = output / 'elmatrix.pyz'
        fd, temp = tempfile.mkstemp(prefix='.elmatrix-build-', dir=output)
        os.close(fd)
        try:
            zipapp.create_archive(staging, temp, interpreter='/usr/bin/env python3')
            os.chmod(temp, 0o700)
            subprocess.run([sys.executable, '-I', temp, '--version'], check=True, capture_output=True, timeout=20)
            subprocess.run([sys.executable, '-I', temp, 'providers'], check=True, capture_output=True, timeout=20)
            sync_file(temp)
            os.replace(temp, archive)
            sync_dir(output)
        finally:
            Path(temp).unlink(missing_ok=True)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        # Replace the manifest itself, never follow an existing symlink/hardlink.
        fd, manifest = tempfile.mkstemp(prefix='.elmatrix-checksum-', dir=output)
        try:
            with os.fdopen(fd, 'w', encoding='ascii') as handle:
                handle.write(digest + '  elmatrix.pyz\n')
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(manifest, output / 'SHA256SUMS')
            sync_dir(output)
        finally:
            Path(manifest).unlink(missing_ok=True)
        return archive


def install(archive, bindir):
    # Only elmatrix is replaced; no ish launchers, environments or data are edited.
    bindir = Path(bindir).expanduser().absolute()
    if any(p.is_symlink() for p in [bindir, *bindir.parents]):
        raise ValueError('bin path must not contain symlinks')
    bindir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if bindir.stat().st_uid != os.getuid():
        raise ValueError('bin directory must belong to the current user')
    target = bindir / 'elmatrix'
    with lock(bindir / '.elmatrix-install.lock'):
        if target.exists() or target.is_symlink():
            regular_file(target)
            backup = Path(tempfile.mkdtemp(prefix='elmatrix-backup-', dir=bindir))
            shutil.copy2(target, backup / 'elmatrix')
            print('Previous command saved in ' + str(backup))
        fd, name = tempfile.mkstemp(prefix='.elmatrix-install-', dir=bindir)
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(archive.read_bytes())
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(name, 0o700)
            # Check the real shebang/runtime before replacing the old command.
            subprocess.run([name, '--version'], check=True, capture_output=True, timeout=20)
            os.replace(name, target)
            sync_dir(bindir)
        finally:
            Path(name).unlink(missing_ok=True)
    print('Installed standalone command: ' + str(target))
    print('Run: export PATH="$HOME/.local/bin:$PATH"')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'elmatrix')
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--bin-dir', type=Path, default=Path.home() / '.local' / 'bin')
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error('Python 3.10+ required')
    archive = build(args.output)
    if args.install:
        install(archive, args.bin_dir)
    print('Deployment bundle: ' + str(archive))


if __name__ == '__main__':
    main()
