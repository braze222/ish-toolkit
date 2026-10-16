from pathlib import Path
import pytest
from tools import crypt


@pytest.fixture
def keys(tmp_path, monkeypatch):
    directory = tmp_path / 'keys'
    monkeypatch.setattr(crypt, 'KDIR', directory)
    monkeypatch.setattr(crypt, 'PRIV', directory / 'id.key')
    monkeypatch.setattr(crypt, 'PUB', directory / 'id.pub')
    crypt.keygen()
    return tmp_path


def test_encrypt_decrypt_and_refuse_overwrite(keys):
    source = keys / 'plain'
    source.write_bytes(b'private contents')
    encrypted = keys / 'encrypted'
    restored = keys / 'restored'
    crypt.enc(source, encrypted)
    crypt.dec(encrypted, restored)
    assert restored.read_bytes() == source.read_bytes()
    assert restored.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        crypt.dec(encrypted, source)
    assert source.read_bytes() == b'private contents'
    with pytest.raises(FileExistsError):
        crypt.enc(source, encrypted)


def test_tampered_ciphertext_does_not_create_output(keys):
    source = keys / 'plain'
    source.write_bytes(b'value')
    encrypted = keys / 'encrypted'
    output = keys / 'out'
    crypt.enc(source, encrypted)
    data = bytearray(encrypted.read_bytes())
    data[-1] ^= 1
    encrypted.write_bytes(data)
    with pytest.raises(SystemExit):
        crypt.dec(encrypted, output)
    assert not output.exists()


def test_directory_temp_cleanup_on_failure(keys, monkeypatch):
    source = keys / 'folder'
    source.mkdir()
    (source / 'secret').write_text('value')
    captured = []
    def fail(path, output):
        captured.append(path)
        raise RuntimeError('test failure')
    monkeypatch.setattr(crypt, 'enc', fail)
    with pytest.raises(RuntimeError):
        crypt.encdir(source)
    assert captured and not captured[0].parent.exists()
