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
exec "$PYTHON" "$ROOT/scripts/install.py" "$@"
