#!/usr/bin/env python3

import platform
import shutil
import subprocess


def exists(command):
    return shutil.which(command) is not None


def check(command, args=None):
    if not exists(command):
        return False

    try:
        result = subprocess.run(
            [command] + (args or []),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def local():
    print("LOCAL")
    print("────────────────────────────")
    print(f"OS           {platform.system()}")
    print(f"Architecture {platform.machine()}")
    print(f"Python       {platform.python_version()}")

    print(
        "SSH          "
        + ("READY" if exists("ssh") else "MISSING")
    )

    print(
        "Git          "
        + ("READY" if exists("git") else "MISSING")
    )

    print(
        "curl         "
        + ("READY" if exists("curl") else "MISSING")
    )

    print()


def docker():
    print("DOCKER")
    print("────────────────────────────")

    if not exists("docker"):
        print("CLI          NOT INSTALLED")
        return

    print("CLI          INSTALLED")

    if check("docker", ["info"]):
        print("Engine       ONLINE")
    else:
        print("Engine       NOT CONNECTED")

    print()


def remote():
    print("REMOTE")
    print("────────────────────────────")
    print("No remote hosts configured.")
    print()


def colab():
    print("COLAB")
    print("────────────────────────────")

    if exists("colab"):
        print("CLI          AVAILABLE")
    else:
        print("CLI          NOT INSTALLED")

    print()


def status():
    print()
    print("ISH COMPUTE")
    print("════════════════════════════")
    print()

    local()
    docker()
    remote()
    colab()


def main():
    import sys

    command = sys.argv[1] if len(sys.argv) > 1 else "status"

    if command == "status":
        status()
    elif command == "local":
        local()
    elif command == "docker":
        docker()
    elif command == "remote":
        remote()
    elif command == "colab":
        colab()
    else:
        print("Usage: ish-compute [status|local|docker|remote|colab]")


if __name__ == "__main__":
    main()
