#!/bin/sh
# Run only after reviewing this checkout inside your authorized cloud console.
# No curl|sh, sudo, global pip, credential extraction or resource provisioning.
set -eu
umask 077
command -v git >/dev/null || { echo 'Git is required in this console.' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Python 3.10+ is required.' >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 - "$SOURCE" <<'PY'
import os, pathlib, platform, subprocess, sys
source = pathlib.Path(sys.argv[1]).resolve()
if sys.version_info < (3,10):
    raise SystemExit('Python 3.10 or newer required')
print('Platform:', platform.system(), platform.machine())
provider = ('Google Cloud Shell hint' if os.environ.get('CLOUD_SHELL') == 'true' else
            'AWS CloudShell hint' if os.environ.get('AWS_EXECUTION_ENV','').startswith('CloudShell') else
            'Azure Cloud Shell hint' if os.environ.get('ACC_CLOUD') else 'unverified interactive environment')
print('Environment:', provider, '(environment variables are not identity proof)')
origin = subprocess.check_output(['git','-C',str(source),'remote','get-url','origin'], text=True).strip()
if origin not in ('https://github.com/braze222/ish-toolkit.git','https://github.com/braze222/ish-toolkit'):
    raise SystemExit('Unexpected origin: verify the checkout manually. No changes made.')
if subprocess.check_output(['git','-C',str(source),'status','--porcelain'], text=True).strip():
    raise SystemExit('Checkout has changes; preserve/review them first. No update attempted.')
# Deliberately never fetch or fast-forward code and then execute it automatically.
# Re-running installs the same reviewed checkout; updating is a separate review step.
venv = source / '.cloud-venv'
if venv.is_symlink():
    raise SystemExit('Refusing symlinked environment')
if venv.exists() and not (venv / 'pyvenv.cfg').is_file():
    raise SystemExit('Existing directory is not a venv; refusing to overwrite')
if not venv.exists():
    subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
python = venv / 'bin/python'
subprocess.run([str(python),'-m','pip','install','-r',str(source/'requirements.txt')],check=True)
subprocess.run([str(python),str(source/'scripts/install.py')],check=True)
print('CLI installed from the reviewed checkout. Keep this source folder.')
print('Run: export PATH="$HOME/.local/bin:$PATH"')
print('Then: ish status; ish selftest --full')
print('Home storage depends on console mode. Runtime processes are not guaranteed to survive session end.')
PY
