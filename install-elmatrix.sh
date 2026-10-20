#!/bin/sh
# Independent local deployment; no downloads, API calls, pip installs or ish edits.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${ELMATRIX_PYTHON:-python3}
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 2)'; then
    echo 'Elmatrix needs Python 3.10+; set ELMATRIX_PYTHON to a working interpreter.' >&2
    exit 2
fi
exec "$PYTHON" "$ROOT/scripts/deploy_elmatrix.py" --install "$@"
