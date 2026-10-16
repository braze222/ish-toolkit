"""Bounded authenticated transports and explicit interactive-console discovery."""
import json
import os
from pathlib import Path
import selectors
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from .model import ComputeError, host_validate
from .worker import safe_text

CONSOLES = {
 'google': {'url': 'https://shell.cloud.google.com/', 'cli': 'gcloud', 'config': '.config/gcloud',
            'docs': 'https://docs.cloud.google.com/shell/docs/quotas-limits',
            'persistence': 'Home storage depends on mode; runtime/session is temporary. Not Compute Engine.',
            'auth': ['gcloud', 'auth', 'list', '--filter=status:ACTIVE', '--format=value(account)']},
 'aws': {'url': 'https://console.aws.amazon.com/cloudshell/', 'cli': 'aws', 'config': '.aws',
         'docs': 'https://docs.aws.amazon.com/cloudshell/latest/userguide/limits.html',
         'persistence': 'Regional home storage; VPC environments differ. Not EC2; API resources may incur charges.',
         'auth': ['aws', 'sts', 'get-caller-identity', '--output', 'json']},
 'azure': {'url': 'https://shell.azure.com/', 'cli': 'az', 'config': '.azure',
           'docs': 'https://learn.microsoft.com/en-us/azure/cloud-shell/overview',
           'persistence': 'Ephemeral or Azure Files storage; storage/resources can incur charges. Not a VM.',
           'auth': ['az', 'account', 'show', '--output', 'json']},
}


def bounded(command, payload=b'', timeout=30, limit=16*1024*1024, env=None):
    """Drain both pipes without retaining stderr or unbounded provider output."""
    p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         env=env, start_new_session=True)
    sel = selectors.SelectSelector()
    os.set_blocking(p.stdout.fileno(), False); sel.register(p.stdout, selectors.EVENT_READ)
    os.set_blocking(p.stdin.fileno(), False)
    if payload:
        sel.register(p.stdin, selectors.EVENT_WRITE)
    else:
        p.stdin.close()
    output = bytearray(); offset = 0; end = time.monotonic() + timeout
    try:
        while sel.get_map():
            if time.monotonic() >= end:
                raise ComputeError('transport timeout; execution may have happened; reconcile, never retry automatically')
            for key, mask in sel.select(0.1):
                if mask & selectors.EVENT_WRITE:
                    try:
                        offset += os.write(p.stdin.fileno(), payload[offset:offset+65536])
                    except BrokenPipeError:
                        offset = len(payload)
                    if offset == len(payload):
                        sel.unregister(p.stdin); p.stdin.close()
                else:
                    data = os.read(p.stdout.fileno(), 65536)
                    if not data:
                        sel.unregister(p.stdout)
                    else:
                        output.extend(data)
                        if len(output) > limit:
                            raise ComputeError('provider response exceeds limit')
        code = p.wait(timeout=max(0.1, end-time.monotonic()))
        if code:
            raise ComputeError('transport failed; check authentication, host fingerprint, executable and connectivity')
        return bytes(output)
    finally:
        sel.close()
        if p.poll() is None:
            p.kill(); p.wait()
        for stream in (p.stdin, p.stdout):
            stream.close()


def ssh_argv(host):
    host_validate('host', host)
    for field in ('identity', 'known_hosts'):
        p = Path(host[field])
        info = p.lstat()
        if p.is_symlink() or not p.is_file() or info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ComputeError('SSH identity/trust file must be owned, regular, not symlinked or group/world writable')
        if field == 'identity' and info.st_mode & 0o077:
            raise ComputeError('SSH private identity must have mode 600 or stricter')
    return ['ssh', '-F', '/dev/null', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'GlobalKnownHostsFile=/dev/null', '-o', 'UserKnownHostsFile=' + shlex.quote(host['known_hosts']),
            '-o', 'IdentitiesOnly=yes', '-o', 'ForwardAgent=no', '-o', 'ClearAllForwardings=yes',
            '-o', 'PermitLocalCommand=no', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=15',
            '-o', 'ServerAliveCountMax=2', '-i', host['identity'], '-p', str(host['port']),
            '-l', host['user'], '--', host['address']]


def endpoint(target, request, timeout=30):
    source = Path(__file__).with_name('worker.py')
    if target is None:
        command = [sys.executable, str(source)]
    else:
        command = ssh_argv(target) + ['python3 -c ' + shlex.quote(source.read_text())]
    env = {k: os.environ[k] for k in ('PATH', 'HOME', 'SSH_AUTH_SOCK', 'LANG') if k in os.environ}
    data = bounded(command, json.dumps(request).encode(), timeout=timeout, env=env)
    try:
        value = json.loads(data)
    except (ValueError, UnicodeError):
        raise ComputeError('invalid endpoint response; remote state unknown') from None
    if not isinstance(value, dict) or 'error' in value:
        raise ComputeError('endpoint rejected operation; inspect permissions and state; do not resubmit blindly')
    return value


def console_status(name, doctor=False):
    c = CONSOLES[name]
    signals = {'google': os.environ.get('CLOUD_SHELL') == 'true',
               'aws': bool(os.environ.get('AWS_EXECUTION_ENV', '').startswith('CloudShell')),
               'azure': bool(os.environ.get('ACC_CLOUD'))}
    result = {'provider': name, 'mode': 'interactive-console-only', 'cli_installed': bool(shutil.which(c['cli'])),
              'configuration_present': (Path.home() / c['config']).exists(),
              'session_hint': signals[name], 'session_verified': False, 'url': c['url'],
              'persistence': c['persistence'], 'quota_remaining': 'unknown; inspect provider console',
              'cost': 'no provisioning by toolkit; resource use/storage may be billed',
              'documentation': c['docs'], 'docs_checked': '2026-10-16', 'execution_api': False}
    result['authentication_required'] = 'official provider login/MFA; CLI configuration is not proof of a live console'
    result['supported_job_types'] = []
    result['availability'] = 'interactive session not verified'
    result['environment_credentials_present'] = bool(
        (os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('AWS_PROFILE')) if name == 'aws' else
        os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') if name == 'google' else
        os.environ.get('AZURE_CLIENT_ID'))
    if doctor:
        try:
            with urllib.request.urlopen(urllib.request.Request(c['url'], method='HEAD'), timeout=5) as response:
                result['network'] = 'official console HTTPS reachable'
        except (urllib.error.URLError, TimeoutError, OSError):
            result['network'] = 'not confirmed; network or provider policy may block access'
        try:
            # The official CLI may use its own configured identity; discard all identity output.
            output = bounded(c['auth'], timeout=20, limit=65536)
            result['authentication'] = ('active cached account configured; API access not verified' if name == 'google' else 'configured identity confirmed') if output.strip() else 'no active identity'
        except (OSError, ComputeError):
            result['authentication'] = 'not confirmed: login, network, policy or CLI failure'
    else:
        result['authentication'] = 'not checked (offline discovery)'
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHub:
    """github.com only; token through official gh credential store or vault, never argv."""
    def __init__(self, profile, token=None):
        self.profile = profile
        if token is None:
            token = bounded(['gh', 'auth', 'token', '--hostname', 'github.com'], limit=8192).decode().strip()
        if not token or len(token) > 8192 or any(c.isspace() for c in token):
            raise ComputeError('invalid GitHub credential')
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())
        self.base = '/repos/' + profile['repo']

    def api(self, path, method='GET', data=None):
        if not path.startswith(self.base + '/') and path != self.base:
            raise ComputeError('API route outside configured repository')
        headers = {'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2026-03-10', 'User-Agent': 'ish-toolkit'}
        request = urllib.request.Request('https://api.github.com' + path,
                    data=json.dumps(data).encode() if data is not None else None, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read(8*1024*1024+1)
                if len(raw) > 8*1024*1024:
                    raise ComputeError('GitHub response exceeds limit')
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            # No raw error bodies or redirect URLs (which can carry signed credentials).
            detail = 'authentication/permissions' if exc.code in (401,403) else 'request/repository/workflow'
            if exc.code == 429 or exc.headers.get('X-RateLimit-Remaining') == '0':
                detail = 'rate limit; wait before an explicit read retry'
            raise ComputeError(f'GitHub HTTP {exc.code}: check {detail}; no automatic dispatch retry') from None
        except (urllib.error.URLError, TimeoutError, ValueError):
            raise ComputeError('GitHub transport/response failure; submission state may be unknown') from None

    def preflight(self):
        repo = self.api(self.base)
        commit = self.api(self.base + '/commits/' + self.profile['ref'])
        if commit.get('sha') != self.profile['commit']:
            raise ComputeError('configured branch/tag moved away from the reviewed commit')
        workflow = self.api(self.base + '/actions/workflows/ish-job.yml')
        if repo.get('archived') or workflow.get('state') != 'active' or workflow.get('path') != '.github/workflows/ish-job.yml':
            raise ComputeError('repository/workflow is not active')
        # Fetch the reviewed immutable workflow and require exactly the bundled contract.
        import base64
        payload = self.api(self.base + '/contents/.github/workflows/ish-job.yml?ref=' + self.profile['commit'])
        expected = Path(__file__).resolve().parents[2] / '.github/workflows/ish-job.yml'
        try:
            actual = base64.b64decode(payload['content']).decode()
        except (KeyError, ValueError, UnicodeError):
            raise ComputeError('cannot verify workflow content') from None
        if actual != expected.read_text():
            raise ComputeError('remote workflow differs from reviewed local contract')
        return {'public': not repo.get('private', True), 'quota': 'unknown', 'cost': 'standard runner policy must be reviewed; artifact storage can be billed'}

    def dispatch(self, job):
        return self.api(self.base + '/actions/workflows/ish-job.yml/dispatches', 'POST',
                        {'ref': self.profile['ref'], 'inputs': {'ish_job_id': job['id'], 'task': job['spec']['task'], 'reviewed_sha': self.profile['commit'],
                                                             'timeout_minutes': str((job['spec']['timeout'] + 59)//60)}})

    def status(self, job):
        run_id = job.get('run_id')
        if run_id is None:
            runs = self.api(self.base + '/actions/workflows/ish-job.yml/runs?event=workflow_dispatch&per_page=100')
            matches = [r for r in runs.get('workflow_runs', []) if r.get('display_title') == 'ish-' + job['id'] and r.get('head_sha') == self.profile['commit']]
            if len(matches) != 1:
                return {'state': 'unknown', 'note': 'no unique endpoint receipt in latest 100 runs; inspect GitHub, never redispatch'}
            run_id = matches[0]['id']
        if type(run_id) is not int or run_id < 1:
            raise ComputeError('invalid workflow run ID')
        run = self.api(self.base + '/actions/runs/' + str(run_id))
        if run.get('display_title') != 'ish-' + job['id'] or run.get('head_sha') != self.profile['commit']:
            raise ComputeError('workflow receipt does not match job identity')
        states = {'queued': 'submitted', 'requested': 'submitted', 'waiting': 'submitted', 'pending': 'submitted', 'in_progress': 'running'}
        conclusions = {'success': 'completed', 'cancelled': 'cancelled', 'timed_out': 'timed_out', 'failure': 'failed', 'action_required': 'failed', 'startup_failure': 'failed', 'skipped': 'failed', 'neutral': 'failed', 'stale': 'failed'}
        state = conclusions.get(run.get('conclusion'), 'unknown') if run.get('status') == 'completed' else states.get(run.get('status'), 'unknown')
        return {'state': state, 'run_id': run_id, 'endpoint': True, 'updated_at': time.time(),
                'jobs': self.api(self.base + '/actions/runs/' + str(run_id) + '/jobs?per_page=100').get('jobs', [])}

    def cancel(self, run_id):
        return self.api(self.base + '/actions/runs/' + str(int(run_id)) + '/cancel', 'POST', {})

    def artifacts(self, run_id):
        return self.api(self.base + '/actions/runs/' + str(int(run_id)) + '/artifacts?per_page=100')

    def archive(self, path):
        # GitHub returns a signed HTTPS storage redirect. Never forward the API token.
        from urllib.parse import urlparse
        request = urllib.request.Request('https://api.github.com' + path,
                    headers={'Authorization': 'Bearer ' + self.token, 'User-Agent': 'ish-toolkit'})
        try:
            self.opener.open(request, timeout=30).close()
            raise ComputeError('expected a signed GitHub archive redirect')
        except urllib.error.HTTPError as exc:
            if exc.code != 302:
                raise ComputeError('archive unavailable, expired or permission denied') from None
            url = exc.headers.get('Location', '')
        parsed = urlparse(url)
        host = parsed.hostname or ''
        if parsed.scheme != 'https' or parsed.username or parsed.port not in (None,443) or not (host.endswith('.blob.core.windows.net') or host.endswith('.githubusercontent.com')):
            raise ComputeError('untrusted archive redirect host')
        try:
            with self.opener.open(urllib.request.Request(url, headers={'User-Agent': 'ish-toolkit'}), timeout=30) as response:
                data = response.read(8*1024*1024+1)
            if len(data) > 8*1024*1024:
                raise ComputeError('archive too large')
            return data
        except (urllib.error.URLError, TimeoutError):
            raise ComputeError('archive transfer failed; signed URL not logged') from None
