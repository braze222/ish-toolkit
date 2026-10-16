"""Explainable selection and durable, non-retrying job orchestration."""
import base64
import getpass
import io
import json
import os
from pathlib import Path
import stat
import time
import uuid
import zipfile
from . import model
from .model import ComputeError
from .providers import endpoint, GitHub
from .worker import file_bytes, safe_text, ARTIFACT_LIMIT, TERMINAL
from ..storage import private_dir, lock


def unlock(refs):
    if not refs:
        return {}
    from ..vault_store import VaultStore
    password = getpass.getpass('Vault master password (never sent to provider): ')
    store = VaultStore()
    from ..vault_store import VaultError
    try:
        values = {key: store.get(ref.removeprefix('vault:'), password) for key, ref in refs.items()}
    except VaultError:
        raise ComputeError('vault unlock/reference failed; verify vault and reference names') from None
    if any(not isinstance(v, str) or not v or len(v.encode()) > 8192 or '\x00' in v for v in values.values()):
        raise ComputeError('vault references must resolve to nonempty UTF-8 values of at most 8192 bytes')
    return values


def github(profile):
    token = unlock({'token': profile['token_ref']}).get('token') if profile['token_ref'] else None
    return GitHub(profile, token)


def compatible(spec, caps):
    reasons = []
    for key, value in spec['requires'].items():
        if value is not False and caps.get(key) != value:
            reasons.append(f'{key} requirement not verified')
    for key, value in spec['resources'].items():
        if caps.get(key) is None or caps[key] < value:
            reasons.append(f'{key} availability insufficient or unknown')
    if spec['type'] == 'docker' and not caps.get('docker'):
        reasons.append('compatible Docker engine not verified')
    return reasons


def select(spec, config, allow_remote=False, allow_cost=False):
    requested = spec['backend']
    candidates = []
    for provider in config['priorities']:
        if provider == 'local':
            candidates.append(('local', None))
        elif provider == 'ssh':
            candidates.extend(('ssh:' + name, host) for name, host in sorted(config['hosts'].items()))
        elif config['github']:
            candidates.append(('github', config['github']))
    if requested != 'auto':
        candidates = [c for c in candidates if c[0] == requested]
        if not candidates:
            raise ComputeError('requested backend is not configured')
    decisions = []
    for name, profile in candidates:
        reasons = []
        remote = name != 'local'
        if remote and not allow_remote:
            reasons.append('requires --allow-remote')
        if name == 'github':
            if spec['type'] != 'workflow':
                reasons.append('GitHub only supports reviewed workflow tasks')
            if not allow_cost:
                reasons.append('Actions quota/storage cost unknown; requires --allow-cost')
            # No secret unlock or API mutation during planning.
            caps = {'mode': 'workflow', 'availability': 'not authenticated during planning'}
        else:
            if spec['type'] == 'workflow':
                reasons.append('workflow requires GitHub')
            if spec['type'] == 'docker' and name == 'local':
                reasons.append('Docker jobs require an explicitly configured SSH host')
            if remote and profile['cost'] != 'existing' and not allow_cost:
                reasons.append('host cost unknown; requires --allow-cost')
            caps = {}
            if not reasons:
                try:
                    caps = endpoint(profile, {'action': 'probe', 'docker': spec['type'] == 'docker'})
                    reasons.extend(compatible(spec, caps))
                except (OSError, ComputeError):
                    reasons.append('endpoint unavailable or identity/capability probe failed')
        decisions.append({'backend': name, 'accepted': not reasons, 'reasons': reasons or ['first compatible authorized backend in configured priority order'], 'capabilities': caps})
        if not reasons:
            return name, profile, decisions
    raise ComputeError('no compatible authorized backend: ' + json.dumps(decisions))


def job_dir(job_id):
    if not model.ID.fullmatch(job_id):
        raise ComputeError('invalid job ID')
    base = private_dir(model.root() / 'jobs')
    path = base / job_id
    if path.is_symlink():
        raise ComputeError('unsafe job directory')
    return path


def read_job(job_id):
    job = model.read(job_dir(job_id) / 'job.json')
    if job.get('id') != job_id or job.get('state') not in model.STATES:
        raise ComputeError('invalid job metadata')
    model.validate(job['spec'])
    if job['backend'].startswith('ssh:'):
        model.host_validate(job['backend'][4:], job['target'])
    elif job['backend'] == 'github':
        model.github_validate(job['target'])
    elif job['backend'] != 'local':
        raise ComputeError('invalid job backend')
    return job


def save_job(job):
    model.write(job_dir(job['id']) / 'job.json', job)


def merge_receipt(job, receipt):
    if receipt.get('state') not in model.STATES:
        raise ComputeError('invalid endpoint state')
    job.update(state=receipt['state'], observed_at=time.time(), evidence='endpoint')
    for key in ('run_id', 'exit_code', 'note'):
        if key in receipt:
            job[key] = receipt[key]
    # Store only bounded job summaries, never arbitrary endpoint steps/output.
    if 'jobs' in receipt:
        job['workflow_jobs'] = [{'id': j.get('id'), 'status': j.get('status'), 'conclusion': j.get('conclusion')} for j in receipt['jobs'][:100]]


def submit(spec, *, execute=False, allow_remote=False, allow_secrets=False, allow_cost=False):
    spec = model.validate(spec)
    name, target, explanation = select(spec, model.config(), allow_remote, allow_cost)
    if not execute:
        return {'dry_run': True, 'backend': name, 'decisions': explanation,
                'note': 'no workload executed; remote planning may probe an explicitly permitted host'}
    if spec['env_refs'] and not allow_secrets:
        raise ComputeError('vault environment delivery requires --allow-secrets and trust in the workload and host')
    if spec['inputs'] and spec['cwd']:
        raise ComputeError('input uploads require a private job workspace (cwd=null)')
    inputs = {}; total = 0
    for name_in, source in spec['inputs'].items():
        p = Path(source)
        data = file_bytes(p.parent, p.name, ARTIFACT_LIMIT - total); total += len(data)
        inputs[name_in] = base64.b64encode(data).decode()
    environment = unlock(spec['env_refs'])
    client = github(target) if name == 'github' else None
    if client:
        client.preflight()
    job_id = uuid.uuid4().hex
    directory = job_dir(job_id); directory.mkdir(mode=0o700)
    job = {'version': 1, 'id': job_id, 'spec': spec, 'backend': name, 'target': target,
           'state': 'queued', 'created_at': time.time(), 'evidence': 'local',
           'permissions': {'execute': True, 'remote': allow_remote, 'secrets': allow_secrets, 'cost': allow_cost},
           'selection': explanation}
    with lock(directory / '.lock'):
        save_job(job)
        # Persist before sending. A crash after this write is ambiguous, never a safe retry.
        job.update(state='submitted', evidence='local-intent'); save_job(job)
    try:
        if client:
            dispatched = client.dispatch(job)
            if type(dispatched.get('workflow_run_id')) is int:
                job['run_id'] = dispatched['workflow_run_id']
            merge_receipt(job, client.status(job))
        else:
            receipt = endpoint(target, {'action': 'run', 'id': job_id, 'spec': spec,
                                       'environment': environment, 'input_data': inputs}, timeout=spec['timeout'] + 45)
            merge_receipt(job, receipt)
    except (OSError, ComputeError, KeyboardInterrupt):
        job.update(state='unknown', evidence='local-transport-failure',
                   note='execution may have happened; use jobs inspect --refresh; no automatic retry')
    with lock(directory / '.lock'):
        save_job(job)
    return job


def refresh(job_id, action='status'):
    directory = job_dir(job_id)
    with lock(directory / '.lock'):
        job = read_job(job_id)
        try:
            if job['backend'] == 'github':
                client = github(job['target'])
                receipt = client.status(job)
                merge_receipt(job, receipt)
                if action == 'cancel' and job.get('run_id'):
                    client.cancel(job['run_id'])
                    job['note'] = 'cancellation requested; refresh to confirm endpoint state'
            else:
                receipt = endpoint(job['target'], {'action': action, 'id': job_id})
                merge_receipt(job, receipt)
            save_job(job)
        except (OSError, ComputeError):
            # Preserve terminal evidence; inability to refresh does not undo it.
            if job['state'] not in TERMINAL:
                job.update(state='unknown', evidence='refresh-failed')
            job['note'] = 'endpoint unavailable; last confirmed receipt retained where terminal'
            save_job(job)
        return job


def zip_files(data):
    files = {}; total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if len(archive.infolist()) > 128:
            raise ComputeError('archive member limit exceeded')
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            model.relative(entry.filename)
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG)) or entry.filename in files or entry.flag_bits & 1:
                raise ComputeError('unsafe archive member')
            total += entry.file_size
            if total > ARTIFACT_LIMIT:
                raise ComputeError('expanded archive exceeds 8 MiB')
            with archive.open(entry) as f:
                value = f.read(ARTIFACT_LIMIT + 1)
            if len(value) != entry.file_size:
                raise ComputeError('invalid archive size')
            files[entry.filename] = value
    return files


def logs(job_id):
    job = read_job(job_id)
    if job['backend'] == 'github':
        if not job.get('run_id'):
            raise ComputeError('refresh to find the workflow run first')
        client = github(job['target'])
        files = zip_files(client.archive(client.base + '/actions/runs/' + str(job['run_id']) + '/logs'))
        # GitHub masks configured secrets; local sanitization strips controls and known token forms.
        return {'text': safe_text('\n'.join(v.decode('utf-8', 'replace') for v in files.values()), [client.token])}
    response = endpoint(job['target'], {'action': 'logs', 'id': job_id})
    return {'text': safe_text(str(response.get('text', ''))), 'note': response.get('note')}


def artifacts(job_id, destination=None, artifact_id=None):
    job = read_job(job_id)
    if job['backend'] == 'github':
        if not job.get('run_id'):
            raise ComputeError('refresh to find the workflow run first')
        client = github(job['target'])
        listing = client.artifacts(job['run_id'])
        if destination is None:
            return {'artifacts': [{'id': a['id'], 'name': safe_text(a['name']), 'expired': a['expired'], 'size_in_bytes': a['size_in_bytes']} for a in listing.get('artifacts', [])]}
        if artifact_id not in [a['id'] for a in listing.get('artifacts', []) if not a['expired']]:
            raise ComputeError('choose a nonexpired artifact ID from this run')
        files = zip_files(client.archive(client.base + '/actions/artifacts/' + str(artifact_id) + '/zip'))
    else:
        if destination is None:
            return {'requested_outputs': job['spec']['outputs'], 'note': 'not yet fetched or verified; use --destination NEW_DIRECTORY'}
        result = endpoint(job['target'], {'action': 'artifacts', 'id': job_id})
        if set(result.get('files', {})) != set(job['spec']['outputs']):
            raise ComputeError('endpoint artifact set differs from requested outputs')
        files = {k: base64.b64decode(v, validate=True) for k,v in result['files'].items()}
    if sum(map(len, files.values())) > ARTIFACT_LIMIT:
        raise ComputeError('artifact total exceeds limit')
    destination = Path(destination).expanduser().absolute()
    for p in [*destination.parents, destination]:
        if p.is_symlink():
            raise ComputeError('artifact destination contains a symlink')
    destination.mkdir(mode=0o700)  # no overwrite, including an existing empty directory
    import hashlib
    manifest = {}
    for name, data in files.items():
        model.relative(name)
        path = destination / name
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as f:
            f.write(data)
        manifest[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return {'destination': str(destination), 'files': manifest, 'note': 'untrusted data, never executed automatically; checksums are transport records, not provenance signatures'}
