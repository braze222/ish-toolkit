import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
from lib.orchestration import providers

ROOT = Path(__file__).resolve().parents[1]


def test_control_profile_without_third_party_packages(tmp_path):
    venv = tmp_path/'venv'
    subprocess.run([sys.executable,'-m','venv','--without-pip',str(venv)],check=True)
    python=venv/'bin/python'; bindir=tmp_path/'bin'
    env=dict(os.environ,HOME=str(tmp_path),ISH_PYTHON=str(python))
    missing=subprocess.run([str(python),'-c','import cryptography'],env=env,capture_output=True)
    assert missing.returncode != 0
    install=subprocess.run(['sh',str(ROOT/'install.sh'),'--profile','control','--bin-dir',str(bindir)],env=env,capture_output=True,text=True)
    assert install.returncode==0, install.stderr
    for args in [('compatibility',),('selftest','--control'),('status',)]:
        result=subprocess.run([str(bindir/'ish'),*args],env=env,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
    result=subprocess.run([str(bindir/'ish'),'vault','verify'],env=env,capture_output=True,text=True)
    assert result.returncode==2 and 'full security dependencies' in result.stderr and 'Traceback' not in result.stderr
    assert not (tmp_path/'.vault').exists()
    assert not (bindir/'vault').exists()
    full=subprocess.run(['sh',str(ROOT/'install.sh'),'--profile','full','--bin-dir',str(bindir)],env=env,capture_output=True,text=True)
    assert full.returncode != 0
    assert subprocess.run([str(bindir/'ish'),'compatibility'],env=env,capture_output=True).returncode==0


def test_no_default_selector_dependency(monkeypatch):
    def unsupported(): raise OSError('emulated kernel does not support epoll')
    monkeypatch.setattr(selectors,'DefaultSelector',unsupported)
    assert providers.bounded([sys.executable,'-c','print("portable")']).strip()==b'portable'


def test_diagnostics_omit_secret_environment(tmp_path):
    secret='private-diagnostic-test-value'
    env=dict(os.environ,HOME=str(tmp_path),AWS_SECRET_ACCESS_KEY=secret)
    for cmd in (['sh',str(ROOT/'scripts/compatibility.sh')],[sys.executable,str(ROOT/'tools/ish-compatibility.py')]):
        p=subprocess.run(cmd,env=env,capture_output=True,text=True)
        assert p.returncode==0 and secret not in p.stdout+p.stderr
    report=json.loads(p.stdout)
    assert report['imports_and_crypto_verified'] is False


def test_missing_interpreter_reports_actionable_error(tmp_path):
    p=subprocess.run(['sh',str(ROOT/'install.sh')],env=dict(os.environ,HOME=str(tmp_path),ISH_PYTHON='/missing-python'),capture_output=True,text=True)
    assert p.returncode==2 and 'compatibility.sh' in p.stderr
