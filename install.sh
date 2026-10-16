#!/bin/sh
# Install this local source tree. No downloads, repository edits, or OS upgrades.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${ISH_PYTHON:-}" ]; then
    PYTHON=$ISH_PYTHON
elif [ -x "$HOME/venv/bin/python" ]; then
    PYTHON=$HOME/venv/bin/python
else
    PYTHON=python3
fi
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo 'Python is missing or ISH_PYTHON is invalid. Run: sh scripts/compatibility.sh' >&2
    exit 2
fi
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 2)'; then
    echo 'Python 3.10+ must start successfully. Run: sh scripts/compatibility.sh' >&2
    echo 'Preserve your filesystem before updating Alpine; no automatic OS upgrade is performed.' >&2
    exit 2
fi
exec "$PYTHON" "$ROOT/scripts/install.py" "$@"
