"""Self-contained stdlib endpoint sent over verified SSH. No shell or daemon.

Endpoint files belong to the executing account; this is not a sandbox against
that account or against hostile code given its permissions.
"""
import base64
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

LIMIT = 1024 * 1024
ARTIFACT_LIMIT = 8 * 1024 * 1024
TERMINAL = {'completed', 'failed', 'cancelled', 'timed_out'}


def safe_text(text, secrets=()):
    for value in sorted(set(secrets), key=len, reverse=True):
        if value:
            text = text.replace(value, '[REDACTED]')
    text = re.sub(r'(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})', '[REDACTED]', text)
    return ''.join(c if c in '\n\t' or (c.isprintable() and ord(c) != 127) else '\\u%04x' % ord(c) for c in text)


def private(path):
    path = Path(path).absolute()
    for p in [*reversed(path.parents), path]:
        if p.is_symlink():
            raise ValueError('managed path contains a symlink')
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.stat().st_uid != os.getuid():
        raise ValueError('managed directory not owned by current user')
    path.chmod(0o700)
    return path


def save(path, data):
    if path.is_symlink():
        raise ValueError('unsafe state path')
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        Path(name).unlink(missing_ok=True)


def load(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as f:
        info = os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 65536 or info.st_uid != os.getuid():
            raise ValueError('unsafe metadata')
        return json.load(f)


def file_bytes(root, relative, limit=ARTIFACT_LIMIT):
    # Walk with openat/O_NOFOLLOW: a swapped directory symlink cannot escape root.
    parts = relative.split('/')
    if relative.startswith('/') or any(p in ('', '.', '..') for p in parts):
        raise ValueError('unsafe artifact path')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = nxt
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(leaf, 'rb') as f:
            info = os.fstat(f.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
                raise ValueError('artifact must be a bounded regular file with one link')
            data = f.read(limit + 1)
            if len(data) > limit:
                raise ValueError('artifact too large')
            return data
    finally:
        os.close(fd)


def capabilities():
    release = platform.release().lower()
    ish = 'ish' in release or Path('/proc/ish').exists()
    memory = None
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'):
                memory = int(line.split()[1]) // 1024
    except OSError:
        pass
    return {'os': platform.system().lower(), 'arch': platform.machine(), 'full_kernel': not ish and platform.system() == 'Linux',
            'gpu': False, 'tpu': False, 'persistent': False, 'memory_mb': memory,
            'disk_mb': shutil.disk_usage(Path.home()).free // (1024 * 1024), 'cpus': os.cpu_count(),
            'ish': ish, 'python': platform.python_version(), 'measured_at': time.time()}


def run(request, directory):
    spec = request['spec']
    # Atomic mkdir is the idempotency boundary. An existing ID is never executed twice.
    directory.mkdir(mode=0o700)
    parent_fd = os.open(directory.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    work = private(directory / 'work')
    cwd = Path(spec['cwd']) if spec['cwd'] else work
    if not cwd.is_dir() or cwd.is_symlink():
        raise ValueError('working directory missing or unsafe')
    incoming = request.get('input_data', {})
    if incoming and spec['cwd']:
        raise ValueError('inputs require private job workspace')
    total = 0
    for name, encoded in incoming.items():
        if name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/')):
            raise ValueError('invalid input path')
        data = base64.b64decode(encoded, validate=True); total += len(data)
        if total > ARTIFACT_LIMIT:
            raise ValueError('input transfer exceeds 8 MiB')
        target = work / name
        private(target.parent)
        with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as f:
            f.write(data)
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(Path.home()), 'LANG': 'C.UTF-8'}
    secrets = request.get('environment', {})
    env.update(secrets)
    command = spec['command']
    docker = spec['type'] == 'docker'
    if docker:
        resources = spec['resources']
        command = ['docker', 'run', '--rm', '--pull=never', '--name', 'ish-' + request['id'],
                   '--network=none', '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
                   '--pids-limit=128', '--memory=' + str(resources.get('memory_mb', 256)) + 'm',
                   '--cpus=' + str(resources.get('cpus', 1)), '--user=65534:65534',
                   '--tmpfs=/tmp:rw,noexec,nosuid,size=64m', spec['image'], *command]
    state = {'id': request['id'], 'state': 'submitted', 'exit_code': None, 'updated_at': time.time(),
             'cwd': str(cwd), 'outputs': spec['outputs'], 'endpoint': True}
    save(directory / 'state.json', state)
    child = None
    buffer = bytearray()
    interrupted = [False]
    def interrupt(signum, frame):
        interrupted[0] = True
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, interrupt)
    try:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        state.update(state='running', updated_at=time.time())
        save(directory / 'state.json', state)
        selector = selectors.SelectSelector()
        selector.register(child.stdout, selectors.EVENT_READ)
        end = time.monotonic() + spec['timeout']
        forced = None
        # Read while polling so output cannot block timeout or cancellation.
        while True:
            if interrupted[0] or (directory / 'cancel').exists():
                forced = 'cancelled'
            elif time.monotonic() >= end:
                forced = 'timed_out'
            if forced:
                os.killpg(child.pid, signal.SIGKILL)
                if docker:
                    subprocess.run(['docker', 'rm', '-f', 'ish-' + request['id']], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=10, env=env)
            for key, _ in selector.select(0.1):
                data = os.read(key.fileobj.fileno(), 65536)
                if data:
                    buffer.extend(data[:max(0, LIMIT + 8192 - len(buffer))])
                else:
                    selector.unregister(key.fileobj)
            if child.poll() is not None and (not selector.get_map() or forced):
                break
            # Background descendants with stdout open remain bounded by timeout.
        selector.close()
        state.update(state=forced or ('completed' if child.returncode == 0 else 'failed'), exit_code=child.returncode)
    except (OSError, subprocess.SubprocessError):
        if child and child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL); child.wait()
        state.update(state='failed', error='endpoint execution failed; check executable, cwd and permissions')
    finally:
        # Redact before persistence. Discard boundary bytes on truncation so partial
        # secrets cannot leak across a fixed-size capture boundary.
        truncated = len(buffer) > LIMIT
        text = bytes(buffer[:LIMIT] if not truncated else buffer[:max(0, LIMIT - 8192)]).decode('utf-8', 'replace')
        text = safe_text(text, secrets.values())
        if truncated:
            text += '\n[output truncated]\n'
        save(directory / 'log.json', {'text': text})
        state['updated_at'] = time.time()
        save(directory / 'state.json', state)
    return state


def dispatch(request):
    action = request['action']
    if action == 'probe':
        c = capabilities()
        if request.get('docker'):
            try:
                p = subprocess.run(['docker', 'info', '--format', '{{.OSType}}'], capture_output=True, timeout=10,
                                   env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(Path.home())})
                c['docker'] = p.returncode == 0 and p.stdout.strip() == b'linux'
            except (OSError, subprocess.SubprocessError):
                c['docker'] = False
        return c
    job_id = request['id']
    if not re.fullmatch(r'[0-9a-f]{32}', job_id):
        raise ValueError('invalid job ID')
    base = private(private(Path.home() / '.ish-toolkit') / 'compute-endpoint')
    directory = base / job_id
    if directory.is_symlink():
        raise ValueError('unsafe job directory')
    if action == 'run':
        return run(request, directory)
    state = load(directory / 'state.json')
    if action == 'status':
        # running is only a recorded observation, never a fresh liveness claim.
        if state['state'] in ('submitted', 'running'):
            state = dict(state, state='unknown', note='no terminal receipt yet; worker may still be active')
        return state
    if action == 'cancel':
        if state['state'] not in TERMINAL:
            fd = os.open(directory / 'cancel', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            os.close(fd)
        return {'cancel_requested': state['state'] not in TERMINAL, 'state': state['state'] if state['state'] in TERMINAL else 'unknown'}
    if action == 'logs':
        if not (directory / 'log.json').exists():
            return {'text': '', 'note': 'logs are redacted and published at completion'}
        # Logs have their own bounded reader, larger than metadata.
        return json.loads(file_bytes(directory, 'log.json', LIMIT * 8).decode())
    if action == 'artifacts':
        if state['state'] not in TERMINAL:
            raise ValueError('artifacts require a terminal endpoint receipt')
        result = {}; total = 0
        for name in state['outputs']:
            data = file_bytes(state['cwd'], name, ARTIFACT_LIMIT - total); total += len(data)
            result[name] = base64.b64encode(data).decode()
        return {'files': result}
    raise ValueError('unsupported endpoint action')


def main():
    os.umask(0o077)
    try:
        raw = sys.stdin.buffer.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError('request too large')
        response = dispatch(json.loads(raw))
    except Exception:
        # Never echo exception text, commands, paths or credentials from untrusted input.
        response = {'error': 'endpoint rejected request or operation failed; no automatic retry'}
    print(json.dumps(response))

if __name__ == '__main__':
    main()
