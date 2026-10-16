import os
import pytest
from cryptography.hazmat.primitives import serialization
from lib import keys
from lib.storage import StorageError


def test_private_creation_permissions_and_no_overwrite(tmp_path):
    before = os.umask(0)
    try:
        assert keys.create(tmp_path/'keys')
    finally:
        os.umask(before)
    private=tmp_path/'keys/id.key'
    original=private.read_bytes()
    assert private.stat().st_mode & 0o777 == 0o600
    assert not keys.create(private.parent)
    assert private.read_bytes()==original


def test_keygen_rejects_symlink_and_orphan_public(tmp_path):
    directory=tmp_path/'keys';directory.mkdir()
    victim=tmp_path/'victim';victim.write_text('unchanged')
    (directory/'id.key').symlink_to(victim)
    with pytest.raises(StorageError):keys.create(directory)
    assert victim.read_text()=='unchanged'
    (directory/'id.key').unlink()
    (directory/'id.pub').write_bytes(b'x'*32)
    with pytest.raises(StorageError):keys.create(directory)
    assert not (directory/'id.key').exists()


def test_keygen_repairs_missing_public_without_replacing_private(tmp_path):
    keys.create(tmp_path/'keys')
    private=tmp_path/'keys/id.key';original=private.read_bytes()
    (private.parent/'id.pub').unlink()
    assert not keys.create(private.parent)
    assert private.read_bytes()==original
    assert (private.parent/'id.pub').read_bytes()==keys.load(private).public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
