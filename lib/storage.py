"""Private local storage helpers. Fail closed on unsafe paths and busy locks."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import stat
import tempfile


class StorageError(Exception):
    pass


def private_dir(path):
    path = Path(path).expanduser().absolute()
    # Do not follow symlinks in managed state paths.
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise StorageError('managed storage path contains a symlink')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise StorageError('storage directory must be owned by this user')
    path.chmod(0o700)
    return path


def regular_file(path):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
        raise StorageError('expected an owned regular file with one link')
    return path


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def sync_file(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def lock(path):
    """Kernel lock is automatically released when the process exits or is killed."""
    path = Path(path)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise StorageError('unsafe lock file')
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise StorageError('another toolkit operation is using this storage; retry later') from exc
        except PermissionError as exc:
            # iSH can return EPERM for a competing nonblocking flock.
            # Never enter the protected section when acquisition fails.
            raise StorageError('storage lock could not be acquired: permission denied or another operation holds it') from exc
        yield
    finally:
        os.close(fd)


def publish_new(source, destination):
    """Atomically publish a complete file, never replace an existing path.

    Hard-link publication requires source/destination on the same filesystem.
    Callers stage in destination.parent. Unsupported filesystems fail closed.
    """
    source, destination = Path(source), Path(destination)
    sync_file(source)
    os.link(source, destination, follow_symlinks=False)
    # Removing the staging name leaves a single-link file, including on success.
    source.unlink()
    sync_dir(destination.parent)


def write_json_new(path, data):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix='.json-', dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, sort_keys=True, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        publish_new(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def read_json(path):
    path = regular_file(path)
    if path.stat().st_size > 16384:
        raise StorageError('metadata file is too large')
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise StorageError('invalid metadata') from exc
    if not isinstance(value, dict):
        raise StorageError('metadata must be an object')
    return value
