# Node.js on iSH

## Problem

Node 20.15+ crashes with "Illegal instruction" (SIGILL) on iSH.
The emulator lacks the SSE2 PUNPCKHDQ instruction that V8 uses.

## Fix

Install Node 20.8.1 from Alpine 3.18 with its specific libraries:

    cd /tmp
    wget https://dl-cdn.alpinelinux.org/alpine/v3.18/community/x86/nodejs-current-20.8.1-r0.apk
    wget https://dl-cdn.alpinelinux.org/alpine/v3.18/main/x86/icu-data-en-73.2-r2.apk
    wget https://dl-cdn.alpinelinux.org/alpine/v3.18/main/x86/icu-libs-73.2-r2.apk
    wget https://dl-cdn.alpinelinux.org/alpine/v3.18/community/x86/ada-libs-2.5.1-r0.apk

    apk add --allow-untrusted icu-data-en-73.2-r2.apk icu-libs-73.2-r2.apk nodejs-current-20.8.1-r0.apk ada-libs-2.5.1-r0.apk
    apk add npm

## Limits

Node 20.8.1 cannot run packages needing Node 20.19+ (like @noble/hashes@2).
For modern Node, use GitHub Codespaces and SSH in from iSH.
