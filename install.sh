#!/bin/sh
set -e
echo "=== ish-toolkit installer ==="

echo "[1/3] Fixing repos..."
rm -rf /ish
echo "https://dl-cdn.alpinelinux.org/alpine/v3.20/main" > /etc/apk/repositories
echo "https://dl-cdn.alpinelinux.org/alpine/v3.20/community" >> /etc/apk/repositories
apk update >/dev/null 2>&1
apk upgrade >/dev/null 2>&1

echo "[2/3] Installing packages..."
apk add --no-cache bash shadow git curl wget openssh-client \
  python3 py3-pip py3-virtualenv \
  py3-cryptography py3-argon2-cffi py3-otp \
  build-base >/dev/null 2>&1

echo "[3/3] Creating Python venv..."
[ ! -d /root/venv ] && python3 -m virtualenv --system-site-packages /root/venv >/dev/null 2>&1

echo ""
echo "Done. Next:"
echo "  bash"
echo "  source /root/venv/bin/activate"
