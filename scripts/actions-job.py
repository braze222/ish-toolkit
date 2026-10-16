"""Fixed task allowlist; no shell interpolation of workflow inputs."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def main():
    job_id, task, minutes = (os.environ.get(k, '') for k in ('ISH_JOB_ID','ISH_TASK','ISH_TIMEOUT'))
    if not re.fullmatch(r'[0-9a-f]{32}', job_id) or task not in ('smoke','test') or not minutes.isdigit() or not 1 <= int(minutes) <= 60:
        raise SystemExit('Invalid workflow contract input')
    result = {'job_id': job_id, 'task': task, 'state': 'running'}
    code = 1
    try:
        if task == 'smoke':
            subprocess.run([sys.executable,'-m','compileall','-q','lib','tools'], check=True)
            subprocess.run([sys.executable,'tools/ish.py','--version'], check=True)
        else:
            subprocess.run([sys.executable,'-m','pip','install','-r','requirements-dev.txt'], check=True)
            subprocess.run([sys.executable,'-m','pytest','-q'], check=True)
        code = 0
    finally:
        result['state'] = 'completed' if code == 0 else 'failed'
        Path('ish-result.json').write_text(json.dumps(result) + '\n')
    return code

if __name__ == '__main__':
    raise SystemExit(main())
