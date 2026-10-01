# Troubleshooting

## Bad system call / Segmentation fault

iSH emulator doesn't implement every syscall. Known failures:
- tmux: cannot run, use iSH's tab bar instead
- Node 20.15+: install 20.8.1
- Some Python urllib calls: use curl via subprocess

## Terminal glitching

Long prompt paths cause redraw bugs. Use \W (basename only) not \w in PS1.

## Boot loops

Never edit /etc/passwd or /etc/profile. Type `bash` manually each session.

## apk unable to select packages

Repos are stale. Fix:

    rm -rf /ish
    echo "https://dl-cdn.alpinelinux.org/alpine/v3.20/main" > /etc/apk/repositories
    echo "https://dl-cdn.alpinelinux.org/alpine/v3.20/community" >> /etc/apk/repositories
    apk update

## Storage full

Check with df -h. Remove /var/cache/apk/* and /tmp/*
