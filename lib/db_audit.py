"""Private JSONL operation log; excludes paths, SQL, values, and credentials.

This is a local append log, not a tamper-proof audit trail.
"""
import json
import os
import stat
import time
from pathlib import Path


class AuditLog:
    def __init__(self, path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    def record(self, action, *, database=None, success=True, metadata=None):
        if action not in {'init', 'query', 'tables', 'schema', 'backup', 'restore', 'doctor'}:
            raise ValueError('unknown audit action')
        # The legacy optional arguments are deliberately never serialized.
        event = {'timestamp': int(time.time()), 'action': action, 'success': bool(success)}
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
        fd = os.open(self.path, flags, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                raise OSError('audit path must be an owned regular file')
            os.fchmod(fd, 0o600)
            data = (json.dumps(event, sort_keys=True) + '\n').encode()
            if os.write(fd, data) != len(data):
                raise OSError('incomplete audit write')
            os.fsync(fd)
        finally:
            os.close(fd)
