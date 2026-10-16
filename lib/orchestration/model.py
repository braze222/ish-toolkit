"""Versioned configuration and job validation. Permissions come from CLI, never JSON."""
import json
import os
from pathlib import Path
import re
import tempfile
from ..storage import private_dir, regular_file, lock, sync_dir

class ComputeError(Exception):
    pass

NAME = re.compile(r'[a-z][a-z0-9-]{0,47}\Z')
ID = re.compile(r'[0-9a-f]{32}\Z')
MAX_JSON = 65536
STATES = {'queued', 'submitted', 'running', 'completed', 'failed', 'cancelled', 'timed_out', 'unknown'}

def root():
    return private_dir(private_dir(Path.home() / '.ish-toolkit') / 'compute')

def read(path):
    path = regular_file(path)
    if path.stat().st_mode & 0o077:
        raise ComputeError('compute metadata must be private (chmod 600)')
    if path.stat().st_size > MAX_JSON:
        raise ComputeError('metadata exceeds size limit')
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ComputeError('expected a JSON object')
    return value

def write(path, value):
    path = Path(path)
    if path.exists() or path.is_symlink():
        regular_file(path)
    data = json.dumps(value, sort_keys=True, indent=2)
    if len(data.encode()) > MAX_JSON:
        raise ComputeError('metadata exceeds size limit')
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.state-')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(data + '\n'); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
        sync_dir(path.parent)
    finally:
        Path(name).unlink(missing_ok=True)

def default_config():
    return {'version': 1, 'priorities': ['local', 'ssh', 'github'], 'hosts': {}, 'github': None}

def config():
    path = root() / 'config.json'
    c = read(path) if path.exists() or path.is_symlink() else default_config()
    if set(c) != {'version', 'priorities', 'hosts', 'github'} or c['version'] != 1:
        raise ComputeError('unsupported compute configuration')
    if not isinstance(c['priorities'], list) or sorted(c['priorities']) != ['github', 'local', 'ssh']:
        raise ComputeError('priorities must contain local, ssh, github exactly once')
    if not isinstance(c['hosts'], dict):
        raise ComputeError('invalid hosts')
    for name, h in c['hosts'].items():
        host_validate(name, h)
    if c['github'] is not None:
        github_validate(c['github'])
    return c

def mutate(fn):
    with lock(root() / '.config.lock'):
        c = config(); fn(c); write(root() / 'config.json', c)

def host_validate(name, h):
    if not NAME.fullmatch(name) or not isinstance(h, dict) or set(h) != {'address', 'user', 'port', 'identity', 'known_hosts', 'cost'}:
        raise ComputeError('invalid host profile')
    for field in ('address', 'user'):
        pattern = r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,252}' if field == 'address' else r'[A-Za-z_][A-Za-z0-9_-]{0,63}'
        if not isinstance(h[field], str) or not re.fullmatch(pattern, h[field]):
            raise ComputeError('invalid host address or username')
    if type(h['port']) is not int or not 1 <= h['port'] <= 65535 or h['cost'] not in ('existing', 'unknown'):
        raise ComputeError('invalid port or cost policy')
    for field in ('identity', 'known_hosts'):
        if not isinstance(h[field], str) or not Path(h[field]).is_absolute() or any(c in h[field] for c in '\n\r\x00'):
            raise ComputeError('identity and known_hosts need absolute paths')

def github_validate(g):
    if not isinstance(g, dict) or set(g) != {'repo', 'ref', 'commit', 'workflow', 'token_ref', 'cost'}:
        raise ComputeError('invalid GitHub configuration')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*', g['repo']):
        raise ComputeError('expected GitHub owner/repository')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./-]{0,199}', g['ref']) or '..' in g['ref'] or not re.fullmatch(r'[0-9a-f]{40}', g['commit']):
        raise ComputeError('GitHub execution requires a reviewed immutable 40-character commit SHA')
    if g['workflow'] != 'ish-job.yml' or g['cost'] not in ('unknown', 'reviewed'):
        raise ComputeError('only the reviewed ish-job.yml contract is supported')
    if g['token_ref'] is not None and not re.fullmatch(r'vault:[A-Za-z0-9_.-]{1,80}', g['token_ref']):
        raise ComputeError('token_ref must be a vault reference, never a token')

def relative(value):
    if not isinstance(value, str) or len(value) > 240 or not value or '\\' in value or any(ord(c) < 32 for c in value):
        raise ComputeError('invalid artifact path')
    p = Path(value)
    if p.is_absolute() or any(x in ('..', '.') for x in value.split('/')) or '' in value.split('/'):
        raise ComputeError('artifact paths must be relative, without traversal')
    return value

def validate(spec):
    fields = {'version', 'type', 'command', 'cwd', 'requires', 'timeout', 'resources', 'env_refs', 'inputs', 'outputs', 'backend', 'task', 'image'}
    if not isinstance(spec, dict) or set(spec) - fields:
        raise ComputeError('unknown job fields; permission grants cannot come from a job file')
    s = dict(version=1, type='command', command=[], cwd=None, requires={}, timeout=300,
             resources={}, env_refs={}, inputs={}, outputs=[], backend='auto', task=None, image=None)
    s.update(spec)
    if type(s['version']) is not int or s['version'] != 1 or s['type'] not in ('command', 'workflow', 'docker'):
        raise ComputeError('unsupported job version/type')
    if type(s['timeout']) is not int or not 1 <= s['timeout'] <= 3600:
        raise ComputeError('timeout must be 1..3600 seconds')
    if not isinstance(s['command'], list) or len(s['command']) > 128 or any(not isinstance(a, str) or '\x00' in a or len(a) > 4096 for a in s['command']):
        raise ComputeError('command must be a bounded argv array')
    if s['type'] != 'workflow' and (not s['command'] or not s['command'][0]):
        raise ComputeError('command is required; shell expansion is never implicit')
    if s['cwd'] is not None and (not isinstance(s['cwd'], str) or not Path(s['cwd']).is_absolute() or '\x00' in s['cwd']):
        raise ComputeError('cwd must be an absolute path or null (private job workspace)')
    if not isinstance(s['requires'], dict) or set(s['requires']) - {'os', 'arch', 'full_kernel', 'gpu', 'tpu', 'persistent'}:
        raise ComputeError('unsupported capability requirement')
    for k, v in s['requires'].items():
        if k in ('os', 'arch'):
            if not isinstance(v, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', v):
                raise ComputeError('invalid os/arch')
        elif type(v) is not bool:
            raise ComputeError('capability flags must be booleans')
    if not isinstance(s['resources'], dict) or set(s['resources']) - {'memory_mb', 'disk_mb', 'cpus'}:
        raise ComputeError('unsupported resource request')
    for v in s['resources'].values():
        if type(v) is not int or not 1 <= v <= 1048576:
            raise ComputeError('resource requests must be positive bounded integers')
    if not isinstance(s['env_refs'], dict) or len(s['env_refs']) > 32:
        raise ComputeError('invalid environment references')
    for key, value in s['env_refs'].items():
        if not re.fullmatch(r'[A-Z_][A-Z0-9_]{0,63}', key) or key.startswith(('LD_', 'DYLD_', 'PYTHON', 'BASH', 'ENV', 'SSH_')) or key in ('PATH', 'HOME', 'SHELLOPTS', 'IFS'):
            raise ComputeError('unsafe environment name')
        if not isinstance(value, str) or not re.fullmatch(r'vault:[A-Za-z0-9_.-]{1,80}', value):
            raise ComputeError('environment values must be vault:name references')
    if not isinstance(s['inputs'], dict) or len(s['inputs']) > 32 or not isinstance(s['outputs'], list) or len(s['outputs']) > 32:
        raise ComputeError('at most 32 input/output files')
    for target, source in s['inputs'].items():
        relative(target)
        if not isinstance(source, str) or not Path(source).is_absolute():
            raise ComputeError('input sources must be absolute local paths')
    for path in s['outputs']:
        relative(path)
    if not isinstance(s['backend'], str) or not re.fullmatch(r'auto|local|github|ssh:[a-z][a-z0-9-]{0,47}', s['backend']):
        raise ComputeError('backend must be auto, local, github or ssh:NAME')
    if s['type'] == 'workflow':
        if s['task'] not in ('smoke', 'test') or s['command'] or s['inputs'] or s['outputs'] or s['env_refs'] or s['cwd'] or s['image'] or s['resources'] or s['requires']:
            raise ComputeError('workflow supports only reviewed smoke/test tasks and timeout')
    elif s['task'] is not None:
        raise ComputeError('task is only valid for workflows')
    if s['type'] == 'docker':
        if not isinstance(s['image'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9./:_-]*@sha256:[0-9a-f]{64}', s['image']):
            raise ComputeError('Docker image must be pinned by sha256 digest')
        if s['env_refs'] or s['inputs'] or s['outputs'] or s['cwd']:
            raise ComputeError('Docker v1 forbids secret env, mounts and artifact paths')
    elif s['image'] is not None:
        raise ComputeError('image is only valid for Docker')
    if len(json.dumps(s).encode()) > 24000:
        raise ComputeError('job spec too large')
    return s
