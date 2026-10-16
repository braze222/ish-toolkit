"""Opt-in real SSH round trip: OpenSSH client + disposable userspace test server.

ISH_TEST_SSH=1 python -m pytest -q tests/test_compute_ssh.py
Requires optional paramiko test dependency. This is loopback, not a cloud-host test.
The test server accepts one generated key, binds only loopback, rejects forwarding,
and launches only this repository's exact endpoint program, never arbitrary commands.
"""
import json
import os
from pathlib import Path
import queue
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
import pytest
from lib.orchestration import model, engine, providers
from lib.orchestration.model import ComputeError

pytestmark = pytest.mark.skipif(os.environ.get('ISH_TEST_SSH') != '1', reason='opt-in real loopback SSH integration')

@pytest.fixture
def ssh_host(tmp_path, monkeypatch):
    paramiko = pytest.importorskip('paramiko')
    if not shutil.which('ssh'): pytest.skip('OpenSSH client required')
    monkeypatch.setenv('HOME',str(tmp_path/'client'));Path.home().mkdir(mode=0o700)
    remote=tmp_path/'endpoint';remote.mkdir(mode=0o700)
    client_key=paramiko.RSAKey.generate(2048);server_key=paramiko.RSAKey.generate(2048)
    key=tmp_path/'client-key';client_key.write_private_key_file(str(key));key.chmod(0o600)
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(16);listener.settimeout(.2)
    port=listener.getsockname()[1]
    known=tmp_path/'known_hosts';known.write_text(f'[127.0.0.1]:{port} {server_key.get_name()} {server_key.get_base64()}\n');known.chmod(0o600)
    source=Path(providers.__file__).with_name('worker.py')
    expected='python3 -c '+shlex.quote(source.read_text())
    stop=threading.Event();errors=queue.Queue();connections=[];threads=[]
    class Server(paramiko.ServerInterface):
        def __init__(self):self.ready=threading.Event()
        def get_allowed_auths(self,username):return 'publickey'
        def check_auth_publickey(self,username,key):
            return paramiko.AUTH_SUCCESSFUL if username=='tester' and key==client_key else paramiko.AUTH_FAILED
        def check_channel_request(self,kind,chanid):
            return paramiko.OPEN_SUCCEEDED if kind=='session' else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        def check_channel_exec_request(self,channel,command):
            if command.decode()!=expected:return False
            self.ready.set();return True
    def serve(client):
        transport=paramiko.Transport(client);connections.append(transport)
        try:
            transport.add_server_key(server_key);server=Server();transport.start_server(server=server)
            channel=transport.accept(10)
            if channel is None or not server.ready.wait(10):return
            payload=bytearray()
            while True:
                chunk=channel.recv(65536)
                if not chunk:break
                payload.extend(chunk)
                if len(payload)>16*1024*1024:raise RuntimeError('request too large')
            result=subprocess.run([sys.executable,str(source)],input=bytes(payload),capture_output=True,
                                  env={'HOME':str(remote),'PATH':'/usr/local/bin:/usr/bin:/bin'},timeout=50)
            channel.sendall(result.stdout);channel.send_exit_status(result.returncode);channel.shutdown_write()
            # Keep channel alive until client receives the complete exit status.
            for _ in range(50):
                if channel.closed:break
                time.sleep(.01)
            channel.close()
            time.sleep(.1)
        except (EOFError, ConnectionError, paramiko.SSHException):
            pass  # Expected for the deliberately incorrect host-key test.
        except Exception as exc:errors.put(exc)
        finally:transport.close()
    def accept():
        while not stop.is_set():
            try:client,_=listener.accept()
            except socket.timeout:continue
            except OSError:break
            thread=threading.Thread(target=serve,args=(client,),daemon=True);threads.append(thread);thread.start()
    acceptor=threading.Thread(target=accept,daemon=True);acceptor.start()
    h=dict(address='127.0.0.1',user='tester',port=port,identity=str(key),known_hosts=str(known),cost='existing')
    model.mutate(lambda c:c['hosts'].update(loopback=h))
    try:yield h,remote
    finally:
        stop.set();listener.close();acceptor.join(2)
        for connection in connections:connection.close()
        for thread in threads:thread.join(2)
        if not errors.empty():raise errors.get()


def test_real_ssh_roundtrip(ssh_host,tmp_path):
    host,remote=ssh_host
    caps=providers.endpoint(host,{'action':'probe'})
    assert caps['os']=='linux' and caps['full_kernel']
    source=tmp_path/'input';source.write_text('remote input')
    job=engine.submit({'backend':'ssh:loopback','command':['python3','-c','from pathlib import Path; print("SSH endpoint executed"); Path("result.txt").write_text(Path("input.txt").read_text().upper())'],
                       'inputs':{'input.txt':str(source)},'outputs':['result.txt'],'timeout':15},execute=True,allow_remote=True)
    assert job['state']=='completed',job
    assert (remote/'.ish-toolkit/compute-endpoint'/job['id']/'state.json').exists()
    assert engine.refresh(job['id'])['state']=='completed'
    assert 'SSH endpoint executed' in engine.logs(job['id'])['text']
    engine.artifacts(job['id'],tmp_path/'downloads')
    assert (tmp_path/'downloads/result.txt').read_text()=='REMOTE INPUT'


def test_real_ssh_rejects_wrong_host_key(ssh_host,tmp_path):
    import paramiko
    host,_=ssh_host
    fake=paramiko.RSAKey.generate(2048)
    Path(host['known_hosts']).write_text(f'[127.0.0.1]:{host["port"]} {fake.get_name()} {fake.get_base64()}\n')
    with pytest.raises(ComputeError):providers.endpoint(host,{'action':'probe'})
