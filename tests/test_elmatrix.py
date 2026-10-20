import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import timedelta
import pytest
from lib.elmatrix import cli

ROOT = Path(__file__).resolve().parents[1]
VIDEO = {'id': 'abcdefghijk', 'snippet': {'title': 'Cleaning tutorial', 'channelId': 'UC' + 'a'*22,
         'channelTitle': 'Example', 'publishedAt': '2026-10-19T12:00:00Z'}, 'statistics': {'viewCount': '123', 'likeCount': '4'}}


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('ELMATRIX_HOME', str(tmp_path / '.elmatrix'))
    monkeypatch.delenv('YOUTUBE_API_KEY', raising=False)
    return tmp_path


def imported(home):
    p = home / 'input.json'
    p.write_text(json.dumps({'items': [VIDEO]}))
    return p


def test_offline_scan_report_trends_and_purge(home, capsys):
    p = imported(home)
    assert cli.main(['scan', '--niche', 'cleaning', '--input', str(p)]) == 0
    scanned = json.loads(capsys.readouterr().out)
    assert scanned['source'] == 'imported-unverified'
    assert scanned['monetization'] == 'unknown'
    state = home / '.elmatrix'
    assert state.stat().st_mode & 0o777 == 0o700
    assert next(state.glob('scan-*')).stat().st_mode & 0o777 == 0o600
    assert cli.main(['report', '--format', 'opencode']) == 0
    out = capsys.readouterr().out
    assert 'Do not generate videos' in out and '123' in out
    assert cli.main(['trends']) == 0
    assert len(json.loads(capsys.readouterr().out)['observations']) == 1
    assert cli.main(['purge', '--all']) == 0
    assert not list(state.glob('scan-*'))


def test_live_scan_adapter_and_key_not_persisted(home, monkeypatch, capsys):
    calls = []
    monkeypatch.setenv('YOUTUBE_API_KEY', 'test-only-credential')
    def api(endpoint, params, key):
        calls.append((endpoint, params, key))
        return {'items': [{'id': {'videoId': VIDEO['id']}}]} if endpoint == 'search' else {'items': [VIDEO]}
    monkeypatch.setattr(cli, 'api', api)
    assert cli.main(['scan', '--query', 'plumbing', '--region', 'ZA']) == 0
    assert [c[0] for c in calls] == ['search', 'videos']
    assert calls[0][1]['safeSearch'] == 'strict'
    assert 'test-only-credential' not in capsys.readouterr().out
    assert 'test-only-credential' not in next((home/'.elmatrix').glob('scan-*')).read_text()


def test_failure_does_not_publish_snapshot(home, monkeypatch):
    monkeypatch.setenv('YOUTUBE_API_KEY', 'dummy')
    monkeypatch.setattr(cli, 'api', lambda *a: {'items': [{'id': 'invalid'}]})
    assert cli.main(['scan']) == 2
    assert not (home/'.elmatrix').exists()


def test_missing_key_no_network(home, monkeypatch):
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)
    monkeypatch.setattr(cli, 'fetch', lambda *a, **kw: pytest.fail('network called'))
    assert cli.main(['scan']) == 2
    assert cli.main(['providers']) == 0


def test_expired_snapshots_pruned(home, capsys):
    assert cli.main(['scan', '--input', str(imported(home))]) == 0
    p = next((home/'.elmatrix').glob('scan-*'))
    d = json.loads(p.read_text()); d['captured_at'] = cli.stamp(cli.now() - timedelta(days=30))
    p.write_text(json.dumps(d))
    assert cli.main(['trends']) == 2
    assert not p.exists()


def test_free_catalog_does_not_treat_missing_prices_as_free():
    d = {'p': {'models': {'free': {'cost': {'input': 0, 'output': 0}}, 'unknown': {},
        'paid': {'cost': {'input': 1, 'output': 0}}, 'bool': {'cost': {'input': False, 'output': False}}}}}
    assert [r['model'] for r in cli.free_models(d)] == ['p/free']


def test_symlink_state_rejected(home):
    target = home / 'elsewhere'; target.mkdir()
    (home/'.elmatrix').symlink_to(target, target_is_directory=True)
    assert cli.main(['scan', '--input', str(imported(home))]) == 2
    assert not list(target.iterdir())


@pytest.mark.parametrize('mutation', [
    {'id': '../../attack'}, {'statistics': {'viewCount': '-1'}}, {'snippet': []}])
def test_bad_provider_data(mutation):
    with pytest.raises(cli.ResearchError):
        cli.videos({'items': [dict(VIDEO, **mutation)]})


def test_terminal_controls_removed():
    assert '\x1b' not in cli.text('title\x1b[31m\n')


def test_trends_does_not_mix_queries(home, capsys):
    p = imported(home)
    for q in ('cleaning', 'repairs'):
        assert cli.main(['scan', '--query', q, '--input', str(p)]) == 0
    capsys.readouterr()
    assert cli.main(['trends']) == 0
    assert len(json.loads(capsys.readouterr().out)['observations']) == 1


def test_deployment_independent_and_reinstall(home):
    bindir = home / 'bin'; bindir.mkdir()
    (bindir/'ish').write_text('existing ish')
    env = dict(os.environ, ELMATRIX_PYTHON=sys.executable)
    args = ['sh', str(ROOT/'install-elmatrix.sh'), '--output', str(home/'bundle'), '--bin-dir', str(bindir)]
    for _ in range(2):
        r = subprocess.run(args, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    r = subprocess.run([str(bindir/'elmatrix'), 'providers'], env=env, capture_output=True, text=True, cwd=home)
    assert r.returncode == 0 and 'inference_enabled' in r.stdout
    assert (bindir/'ish').read_text() == 'existing ish'
    assert len(list(bindir.glob('elmatrix-backup-*'))) == 1
    assert (home/'bundle/SHA256SUMS').exists()


def test_no_redirect_of_api_key():
    assert cli.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.invalid') is None


def test_http_key_header_and_bounded_response(monkeypatch):
    observed = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, n):
            observed['limit'] = n
            return b'{"items": []}'
    class Opener:
        def open(self, request, timeout):
            observed['url'] = request.full_url
            observed['headers'] = dict(request.header_items())
            observed['timeout'] = timeout
            return Response()
    monkeypatch.setattr(cli.urllib.request, 'build_opener', lambda *a: Opener())
    assert cli.api('search', {'q': 'repairs'}, 'private-test-value') == {'items': []}
    assert 'private-test-value' not in observed['url']
    assert observed['headers']['X-goog-api-key'] == 'private-test-value'
    assert observed['limit'] == cli.LIMIT + 1 and observed['timeout'] == 20


def test_http_errors_do_not_leak_credentials(monkeypatch):
    class Opener:
        def open(self, *a, **kw):
            raise OSError('sensitive-value-that-must-not-leak')
    monkeypatch.setattr(cli.urllib.request, 'build_opener', lambda *a: Opener())
    with pytest.raises(cli.ResearchError) as exc:
        cli.fetch('https://models.dev/api.json')
    assert 'sensitive-value' not in str(exc.value)


def test_deploy_refuses_symlink_launcher(home):
    spec = importlib.util.spec_from_file_location('deploy_elmatrix', ROOT/'scripts/deploy_elmatrix.py')
    deploy = importlib.util.module_from_spec(spec); spec.loader.exec_module(deploy)
    archive = home/'bundle.pyz'; archive.write_bytes(b'irrelevant')
    bindir = home/'bin'; bindir.mkdir()
    victim = home/'victim'; victim.write_text('preserve')
    (bindir/'elmatrix').symlink_to(victim)
    with pytest.raises(Exception):
        deploy.install(archive, bindir)
    assert victim.read_text() == 'preserve'
