import errno
import os
import pytest
from lib import storage


def test_ish_eperm_lock_fails_closed_and_closes_descriptor(tmp_path, monkeypatch):
    descriptors = []

    def denied(fd, flags):
        descriptors.append(fd)
        raise PermissionError(errno.EPERM, 'Operation not permitted')

    monkeypatch.setattr(storage.fcntl, 'flock', denied)
    with pytest.raises(storage.StorageError, match='could not be acquired'):
        with storage.lock(tmp_path / 'test.lock'):
            pytest.fail('entered protected section without acquiring lock')
    with pytest.raises(OSError) as error:
        os.fstat(descriptors[0])
    assert error.value.errno == errno.EBADF
