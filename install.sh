#!/bin/sh
set -e
echo "=== ish-toolkit installer ==="

echo "[1/4] Fixing repos..."
rm -rf /ish
echo "https://dl-cdn.alpinelinux.org/alpine/v3.20/main" > /etc/apk/repositories
echo "https://dl-cdn.alpinelinux.org/alpine/v3.20/community" >> /etc/apk/repositories
apk update >/dev/null 2>&1
apk upgrade >/dev/null 2>&1

echo "[2/4] Installing packages..."
apk add --no-cache bash shadow git curl wget openssh-client \
  python3 py3-pip py3-virtualenv \
  py3-cryptography py3-argon2-cffi py3-otp \
  build-base >/dev/null 2>&1

echo "[3/4] Creating Python venv..."
[ ! -d /root/venv ] && python3 -m virtualenv --system-site-packages /root/venv >/dev/null 2>&1

echo "[4/4] Installing security tools..."
mkdir -p /root/.local/bin /root/ish-toolkit/tools
cd /tmp
curl -fsSL https://github.com/braze222/ish-toolkit/archive/refs/heads/main.tar.gz -o ish-toolkit.tar.gz
tar -xzf ish-toolkit.tar.gz
cp ish-toolkit-main/tools/*.py /root/ish-toolkit/tools/
for f in /root/ish-toolkit/tools/*.py; do
  name=$(basename "$f" .py)
  ln -sf "$f" /root/.local/bin/"$name"
  chmod +x "$f"
done
rm -rf /tmp/ish-toolkit*

grep -q 'HOME/.local/bin' /root/.profile 2>/dev/null || \
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> /root/.profile

echo ""
echo "=== done ==="
echo ""
echo "Tools: vault totp crypt shred"
echo ""
echo "Next:"
echo "  bash"
echo "  source /root/venv/bin/activate"
echo "  vault init"
