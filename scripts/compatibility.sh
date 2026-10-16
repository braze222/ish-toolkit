#!/bin/sh
# Read-only baseline diagnostics; works even before toolkit installation.
printf '%s\n' 'iSH Toolkit compatibility report (no credentials or device identifiers)'
printf 'Kernel: '; uname -s -r -m
printf 'Alpine: '; if [ -r /etc/alpine-release ]; then cat /etc/alpine-release; else printf '%s\n' 'not detected'; fi
printf '%s\n' 'iOS version / iPhone model: report manually from Settings; Linux values cannot identify them.'
for candidate in "${ISH_PYTHON:-}" "$HOME/venv/bin/python" python3; do
    [ -n "$candidate" ] || continue
    if command -v "$candidate" >/dev/null 2>&1; then
        "$candidate" -c 'import sys,struct; print("Python:",sys.version.split()[0],"bits:",struct.calcsize("P")*8,"minimum 3.10:",sys.version_info >= (3,10))' 2>/dev/null || printf '%s\n' 'Python failed to start.'
    fi
done
for tool in ssh git busybox apk; do
    if command -v "$tool" >/dev/null 2>&1; then printf '%s: present\n' "$tool"; else printf '%s: missing\n' "$tool"; fi
done
printf '%s\n' 'Send this report, the exact failed command/error, iPhone model, iOS version and iSH app version.'
