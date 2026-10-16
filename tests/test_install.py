import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_installer_preserves_source_and_old_launchers(tmp_path):
    bindir = tmp_path / 'bin with spaces'
    bindir.mkdir()
    previous = bindir / 'ish'
    previous.write_text('#!/bin/sh\necho old\n')
    old = previous.read_bytes()
    env = dict(os.environ, ISH_PYTHON=sys.executable)
    result = subprocess.run(['sh', str(ROOT / 'install.sh'), '--bin-dir', str(bindir)],
                            env=env, cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    backups = list(bindir.glob('ish-toolkit-install-backup-*'))
    assert len(backups) == 1
    assert (backups[0] / 'ish').read_bytes() == old
    env['HOME'] = str(tmp_path)
    result = subprocess.run([str(bindir / 'ish'), 'db', 'doctor'], env=env,
                            cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert 'PASS' in result.stdout
    assert not (bindir / '__init__').exists()
