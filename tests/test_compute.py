"""Compute security regressions; provider API unit tests are explicitly mocked."""
import base64
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import zipfile
import pytest
from lib.orchestration import model, engine, providers, worker
from lib.orchestration.model import ComputeError

@pytest.fixture(autouse=True)
def private_home(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))


def command(code='print("hello")', **kwargs):
    return dict(command=[sys.executable, '-c', code], **kwargs)


def test_dry_run_does_not_execute(tmp_path):
    marker = tmp_path / 'no'
    result = engine.submit(command(f'open({str(marker)!r},"w").write("bad")'))
    assert result['dry_run'] and not marker.exists()
    assert not (model.root() / 'jobs').exists()

@pytest.mark.parametrize('change', [
 {'permissions': {'execute': True}}, {'version': 99}, {'timeout': 0}, {'timeout': True},
 {'requires': {'root': True}}, {'requires': {'gpu': 'yes'}}, {'resources': {'memory_mb': -1}},
 {'env_refs': {'PATH': 'vault:key'}}, {'env_refs': {'TOKEN': 'plaintext'}},
 {'inputs': {'../escape': '/tmp/file'}}, {'outputs': ['/etc/passwd']},
 {'backend': 'ssh:-oProxyCommand=bad'}, {'command': 'echo hi'}, {'command': ['echo', '\x00']},
 {'type':'docker','image':'alpine:latest'},
])
def test_reject_unsafe_specs(change):
    spec = command(); spec.update(change)
    with pytest.raises(ComputeError): model.validate(spec)


def test_private_config_symlink_rejected(tmp_path):
    target = tmp_path / 'other'; target.write_text('untouched')
    (model.root() / 'config.json').symlink_to(target)
    with pytest.raises(Exception): model.mutate(lambda c: None)
    assert target.read_text() == 'untouched'


def test_configuration_permissions_and_roundtrip():
    model.mutate(lambda c: None)
    assert (model.root() / 'config.json').stat().st_mode & 0o777 == 0o600
    assert model.config()['version'] == 1


def test_real_local_job_logs_status_artifacts(tmp_path):
    source = tmp_path / 'input'; source.write_text('sample')
    result = engine.submit(command('from pathlib import Path; print("OK"); Path("out").write_text(Path("in").read_text().upper())',
                         inputs={'in': str(source)}, outputs=['out']), execute=True)
    assert result['state'] == 'completed' and result['exit_code'] == 0
    job_id = result['id']
    assert 'OK' in engine.logs(job_id)['text']
    assert engine.refresh(job_id)['state'] == 'completed'
    out = tmp_path / 'received'
    receipt = engine.artifacts(job_id, out)
    assert (out/'out').read_text() == 'SAMPLE'
    assert receipt['files']['out']['bytes'] == 6
    with pytest.raises(FileExistsError): engine.artifacts(job_id, out)


def test_timeout_and_nonzero_status():
    result = engine.submit(command('import time; time.sleep(10)', timeout=1), execute=True)
    assert result['state'] == 'timed_out'
    result = engine.submit(command('raise SystemExit(7)'), execute=True)
    assert result['state'] == 'failed' and result['exit_code'] == 7


def test_secret_redaction_before_persistence(monkeypatch):
    secret = 'test-private-' + os.urandom(12).hex()
    monkeypatch.setattr(engine, 'unlock', lambda refs: {'TOKEN': secret})
    code = 'import os,sys; v=os.environ["TOKEN"]; sys.stdout.write(v[:5]); sys.stdout.flush(); sys.stdout.write(v[5:]+"\\x1b[31m")'
    result = engine.submit(command(code, env_refs={'TOKEN': 'vault:test'}), execute=True, allow_secrets=True)
    assert result['state'] == 'completed'
    output = engine.logs(result['id'])['text']
    assert secret not in output and '[REDACTED]' in output and '\x1b' not in output
    for path in Path.home().rglob('*.json'):
        assert secret not in path.read_text()


def test_missing_secret_grant_fails_before_unlock(monkeypatch):
    monkeypatch.setattr(engine, 'unlock', lambda r: pytest.fail('must not unlock'))
    with pytest.raises(ComputeError, match='allow-secrets'):
        engine.submit(command(env_refs={'TOKEN':'vault:test'}), execute=True)


def test_no_ambient_credentials():
    os.environ['ISH_TEST_SECRET'] = 'should-not-inherit'
    try:
        result = engine.submit(command('import os; print(os.environ.get("ISH_TEST_SECRET", "absent"))'), execute=True)
        assert 'absent' in engine.logs(result['id'])['text']
    finally:
        del os.environ['ISH_TEST_SECRET']


def test_cancel_running_job_without_pid_signal_race():
    results = []
    thread = threading.Thread(target=lambda: results.append(engine.submit(command('import time; time.sleep(30)', timeout=35), execute=True)))
    thread.start()
    end = time.monotonic() + 5; job_id = None
    while time.monotonic() < end:
        base = Path.home() / '.ish-toolkit/compute-endpoint'
        if base.exists():
            for p in base.glob('*/state.json'):
                if json.loads(p.read_text())['state'] == 'running': job_id = p.parent.name
        if job_id: break
        time.sleep(.05)
    assert job_id
    request = engine.refresh(job_id, 'cancel')
    assert request['state'] in ('unknown','cancelled')
    thread.join(5)
    assert not thread.is_alive() and results[0]['state'] == 'cancelled'


def test_interrupted_submission_is_unknown_without_retry(monkeypatch):
    original = engine.endpoint; calls=[]
    def endpoint(target, req, **kw):
        if req['action'] == 'probe': return original(target, req, **kw)
        calls.append(req)
        raise ComputeError('connection lost')
    monkeypatch.setattr(engine, 'endpoint', endpoint)
    result = engine.submit(command(), execute=True)
    assert result['state'] == 'unknown' and len(calls) == 1


def test_existing_endpoint_id_never_reexecutes():
    spec = model.validate(command())
    request = {'action':'run','id':'a'*32,'spec':spec}
    assert providers.endpoint(None, request)['state'] == 'completed'
    with pytest.raises(ComputeError): providers.endpoint(None, request)


def test_resource_and_arch_constraints_fail_closed():
    with pytest.raises(ComputeError): engine.submit(command(requires={'arch':'imaginary'}))
    with pytest.raises(ComputeError): engine.submit(command(requires={'gpu': True}))
    with pytest.raises(ComputeError): engine.submit(command(requires={'persistent': True}))


def host(tmp_path):
    key=tmp_path/'id'; key.write_text('dummy'); key.chmod(0o600)
    trust=tmp_path/'known'; trust.write_text('dummy'); trust.chmod(0o600)
    return dict(address='example.invalid',user='tester',port=22,identity=str(key),known_hosts=str(trust),cost='existing')


def test_strict_ssh_no_config_proxy_or_agent_forwarding(tmp_path):
    h=host(tmp_path); args=providers.ssh_argv(h)
    assert 'StrictHostKeyChecking=yes' in args and 'ForwardAgent=no' in args
    assert args[1:3] == ['-F','/dev/null'] and args[-2:] == ['--','example.invalid']
    Path(h['identity']).chmod(0o644)
    with pytest.raises(ComputeError): providers.ssh_argv(h)


def test_remote_permission_required_even_in_config(tmp_path, monkeypatch):
    c=model.default_config(); c['hosts']['test']=host(tmp_path)
    monkeypatch.setattr(engine, 'endpoint', lambda *a,**k: pytest.fail('unauthorized probe'))
    with pytest.raises(ComputeError, match='allow-remote'):
        engine.select(model.validate(command(backend='ssh:test')),c)


def test_unknown_host_cost_fails_closed(tmp_path, monkeypatch):
    c=model.default_config(); h=host(tmp_path);h['cost']='unknown';c['hosts']['test']=h
    monkeypatch.setattr(engine, 'endpoint', lambda *a,**k: pytest.fail('unapproved cost probe'))
    with pytest.raises(ComputeError, match='allow-cost'):
        engine.select(model.validate(command(backend='ssh:test')),c,allow_remote=True)


def test_zip_traversal_links_duplicates_and_limits():
    for name, mode in [('../escape',0), ('/absolute',0), ('link',0o120777)]:
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            info=zipfile.ZipInfo(name);info.external_attr=mode<<16;z.writestr(info,'data')
        with pytest.raises(ComputeError): engine.zip_files(stream.getvalue())


def test_artifact_symlink_exfiltration_rejected(tmp_path):
    secret=tmp_path/'private';secret.write_text('do not retrieve')
    result=engine.submit(command(f'import os; os.symlink({str(secret)!r},"out")',outputs=['out']),execute=True)
    with pytest.raises(ComputeError): engine.artifacts(result['id'], tmp_path/'received')
    assert not (tmp_path/'received').exists()


def test_console_discovery_does_not_call_network(monkeypatch):
    monkeypatch.setattr(providers, 'bounded', lambda *a,**k: pytest.fail('discovery must be offline'))
    for name in providers.CONSOLES:
        result=providers.console_status(name)
        assert result['execution_api'] is False and result['mode']=='interactive-console-only'


def test_console_auth_failure_not_success(monkeypatch):
    def fail(*a,**k): raise ComputeError('sensitive diagnostic')
    monkeypatch.setattr(providers,'bounded',fail)
    import urllib.error
    monkeypatch.setattr(providers.urllib.request, 'urlopen', lambda *a, **k: (_ for _ in ()).throw(urllib.error.URLError('offline')))
    result=providers.console_status('google',True)
    assert result['authentication'].startswith('not confirmed')
    assert 'sensitive' not in json.dumps(result)


def test_output_overflow_bounded():
    with pytest.raises(ComputeError, match='limit'):
        providers.bounded([sys.executable,'-c','print("x"*100000)'],limit=100)


def profile():
    return dict(repo='owner/repo',ref='main',commit='a'*40,workflow='ish-job.yml',token_ref=None,cost='unknown')


def test_mock_github_dispatch_and_receipt():
    client=providers.GitHub(profile(),token='dummy-test-only')
    job={'id':'b'*32,'spec':{'task':'smoke','timeout':5}}
    calls=[]
    def api(path,method='GET',data=None):
        calls.append((path,method,data))
        if method=='POST': return {'workflow_run_id':42}
        if 'workflows/ish-job.yml/runs' in path:
            return {'workflow_runs':[{'id':42,'display_title':'ish-'+job['id'],'head_sha':'a'*40}]}
        if '/jobs?' in path: return {'jobs':[]}
        return {'display_title':'ish-'+job['id'],'head_sha':'a'*40,'status':'completed','conclusion':'success'}
    client.api=api
    assert client.dispatch(job)['workflow_run_id']==42
    assert calls[0][2]['ref']=='main'
    assert calls[0][2]['inputs']['reviewed_sha']=='a'*40
    assert client.status(job)['state']=='completed'


def test_mock_github_missing_receipt_is_unknown():
    client=providers.GitHub(profile(),token='dummy-test-only')
    client.api=lambda *a,**k: {'workflow_runs':[]}
    assert client.status({'id':'b'*32})['state']=='unknown'


def test_mock_github_moved_ref_rejected():
    client=providers.GitHub(profile(),token='dummy-test-only')
    client.api=lambda *a,**k: {'sha':'c'*40}
    with pytest.raises(ComputeError,match='moved'): client.preflight()


def test_github_cost_grant_required():
    c=model.default_config();c['github']=profile()
    with pytest.raises(ComputeError,match='allow-cost'):
        engine.select(model.validate({'type':'workflow','task':'smoke','backend':'github'}),c,allow_remote=True)


def test_cli_help_and_offline_status():
    root=Path(__file__).resolve().parents[1]
    for args in [('help',),('config',),('status',),('compute','providers'),('cloud','google','open'),('init',)]:
        p=subprocess.run([sys.executable,str(root/'tools/ish.py'),*args],capture_output=True,text=True)
        assert p.returncode==0,p.stderr


def test_mock_github_error_never_exposes_response_body():
    import urllib.error
    client=providers.GitHub(profile(),token='dummy-test-only')
    class Opener:
        code = 403
        def open(self,*args,**kwargs):
            raise urllib.error.HTTPError('https://api.github.com',self.code,'denied',{},io.BytesIO(b'private-body'))
    client.opener=Opener()
    for code in (403,429):
        client.opener.code=code
        with pytest.raises(ComputeError) as error:client.api('/repos/owner/repo')
        assert 'private-body' not in str(error.value) and str(code) in str(error.value)
        if code==429:assert 'rate limit' in str(error.value)


def test_mock_github_archive_redirect_cannot_steal_token():
    import urllib.error
    client=providers.GitHub(profile(),token='dummy-test-only')
    class Opener:
        def open(self,*args,**kwargs):
            raise urllib.error.HTTPError('https://api.github.com',302,'redirect',{'Location':'https://attacker.invalid/steal'},None)
    client.opener=Opener()
    with pytest.raises(ComputeError,match='untrusted'):client.archive('/repos/owner/repo/actions/runs/1/logs')


def test_huge_output_is_truncated_and_terminal_sanitized():
    job=engine.submit(command('print("z"*1100000)'),execute=True)
    output=engine.logs(job['id'])['text']
    assert job['state']=='completed' and '[output truncated]' in output and len(output)<1100000


def test_mock_docker_flags_and_no_implicit_pull(tmp_path, monkeypatch):
    # Real child process doubles Docker; verifies the executable boundary, not an engine.
    import signal
    image='example/image@sha256:'+'a'*64
    spec=model.validate({'type':'docker','image':image,'command':['echo','safe']})
    original=subprocess.Popen; captured=[]
    def fake(command, **kwargs):
        captured.append(command)
        return original([sys.executable,'-c','print("container-double")'], **kwargs)
    monkeypatch.setattr(worker.subprocess,'Popen',fake)
    handlers={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP)}
    try:
        result=worker.run({'spec':spec,'id':'a'*32},tmp_path/'docker-job')
    finally:
        for sig,handler in handlers.items():signal.signal(sig,handler)
    assert result['state']=='completed'
    argv=captured[0]
    for required in ('--pull=never','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user=65534:65534'):
        assert required in argv
    assert '--privileged' not in argv and '-v' not in argv and argv[-3:]==[image,'echo','safe']
