#!/usr/bin/env python3

import os
import sys
import stat
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

HOME = Path.home()
VAULT = HOME / ".vault"
TOOLKIT = Path(__file__).resolve().parent.parent

issues = []
warnings = []
checks = 0


def run(cmd):
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        ).stdout.strip()
    except Exception:
        return ""


def check(label, ok, detail=""):
    global checks
    checks += 1
    symbol = "[OK]" if ok else "[!!]"

    print(f"{symbol} {label}")

    if detail:
        print(f"     {detail}")

    if not ok:
        issues.append(label)


def warn(label, detail=""):
    print(f"[??] {label}")
    if detail:
        print(f"     {detail}")
    warnings.append(label)


def section(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def audit_environment():
    section("ENVIRONMENT")

    check(
        "Running inside iSH/Linux environment",
        Path("/etc/alpine-release").exists(),
        "iSH exposes an Alpine Linux userspace.",
    )

    check(
        "Root filesystem writable",
        os.access("/", os.W_OK),
        "Expected for the current iSH root environment.",
    )

    check(
        "Python available",
        bool(run(["python3", "--version"])),
    )

    check(
        "Toolkit directory exists",
        TOOLKIT.is_dir(),
        str(TOOLKIT),
    )


def audit_permissions():
    section("PERMISSIONS")

    targets = [HOME / ".profile", VAULT]
    if (VAULT / "vault-v2.db").exists():
        targets.append(VAULT / "vault-v2.db")
    else:
        targets.extend(VAULT / name for name in ("salt", "verify", "vault.db"))

    for path in targets:
        if not path.exists():
            if path == HOME / ".profile":
                warn("~/.profile not found")
            else:
                warn(f"Missing: {path}")
            continue

        mode = stat.S_IMODE(path.stat().st_mode)

        if path.is_dir():
            expected = 0o700
        else:
            expected = 0o600

        check(
            f"Permissions: {path}",
            mode == expected,
            f"mode={oct(mode)}, expected={oct(expected)}",
        )


def audit_processes():
    section("RUNNING PROCESSES")

    output = run(["ps", "aux"])

    if not output:
        warn("Unable to inspect processes")
        return

    lines = output.splitlines()

    print(f"     {len(lines)} process entries visible")

    suspicious_terms = [
        "nc ",
        "netcat",
        "socat",
        "frpc",
        "chisel",
        "ngrok",
        "tcpdump",
        "mitmproxy",
        "ssh -R",
        "ssh -L",
    ]

    found = []

    for line in lines:
        lower = line.lower()

        for term in suspicious_terms:
            if term in lower:
                found.append(line)
                break

    if found:
        warn(
            "Potentially interesting network/pivot processes detected",
            "\n".join("     " + x for x in found[:10]),
        )
    else:
        check("No known suspicious process patterns detected", True)


def audit_network():
    section("NETWORK")

    sockets = run(["netstat", "-tnp"])

    if not sockets:
        sockets = run(["ss", "-tnp"])

    if sockets:
        print(sockets[:4000])
    else:
        warn(
            "Network socket inspection unavailable",
            "Install net-tools if you want additional visibility.",
        )


def audit_ssh():
    section("SSH")

    ssh_dir = HOME / ".ssh"

    if not ssh_dir.exists():
        check("~/.ssh directory", True, "not present")
        return

    mode = stat.S_IMODE(ssh_dir.stat().st_mode)

    check(
        "~/.ssh permissions",
        mode == 0o700,
        f"mode={oct(mode)}",
    )

    private_key_names = {
        "id_rsa",
        "id_ed25519",
        "id_ecdsa",
        "id_dsa",
    }

    problems = []

    try:
        for path in ssh_dir.iterdir():
            if not path.is_file():
                continue

            file_mode = stat.S_IMODE(path.stat().st_mode)
            name = path.name

            # Private keys must not be group/world accessible.
            if name in private_key_names:
                if file_mode != 0o600:
                    problems.append(
                        f"{name}: permissions {oct(file_mode)}, expected 0o600"
                    )

            # Public keys and known_hosts contain public information.
            elif (
                name.endswith(".pub")
                or name in {
                    "known_hosts",
                    "known_hosts.old",
                    "config",
                    "authorized_keys",
                }
            ):
                if file_mode & 0o002:
                    problems.append(
                        f"{name}: world-writable permissions {oct(file_mode)}"
                    )

            # Unknown SSH files should not be writable by group/world.
            else:
                if file_mode & 0o022:
                    problems.append(
                        f"{name}: group/world-writable permissions {oct(file_mode)}"
                    )

    except Exception as e:
        warn("Could not fully inspect SSH directory", str(e))
        return

    if problems:
        warn(
            "SSH permission issues require review",
            "\n".join("     " + x for x in problems),
        )
    else:
        check(
            "SSH file permissions look appropriate",
            True,
        )

def audit_startup():

    section("PERSISTENCE / STARTUP")

    files = [

        HOME / ".profile",

        HOME / ".bashrc",

        HOME / ".bash_profile",

        HOME / ".ashrc",

    ]

    suspicious_terms = [

        "curl ",

        "wget ",

        "nc ",

        "netcat",

        "socat",

        "nohup",

        "setsid",

        "base64 -d",

        "eval ",

        "python -c",

        "python3 -c",

        "sh -c",

    ]

    for path in files:

        if not path.exists():

            continue

        text = path.read_text(errors="replace")

        matches = []

        for line in text.splitlines():

            stripped = line.strip()

            if not stripped or stripped.startswith("#"):

                continue

            lower = stripped.lower()

            for term in suspicious_terms:

                if term in lower:

                    matches.append(stripped)

                    break

        if matches:

            warn(

                f"Review startup file: {path.name}",

                "\n".join("     " + x[:200] for x in matches[:10]),

            )

        else:

            check(f"Startup file reviewed: {path.name}", True)

def audit_documents():
    section("DOCUMENT / FILE AUDIT")

    user_roots = [
        HOME / "Downloads",
        HOME / "Documents",
    ]

    suspicious_extensions = {
        ".exe",
        ".dll",
        ".so",
        ".bin",
        ".scr",
        ".com",
        ".bat",
        ".cmd",
        ".vbs",
        ".vbe",
        ".ps1",
        ".hta",
    }

    script_extensions = {
        ".sh",
        ".bash",
        ".py",
        ".pl",
        ".rb",
        ".php",
    }

    suspicious = []
    scripts = []

    for root in user_roots:
        if not root.exists():
            continue

        try:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue

                suffix = path.suffix.lower()

                if suffix in suspicious_extensions:
                    suspicious.append(path)
                elif suffix in script_extensions:
                    scripts.append(path)

        except Exception:
            continue

    if suspicious:
        warn(
            f"Suspicious executable-like files found: {len(suspicious)}",
            "Presence alone does NOT prove malware.",
        )

        for path in suspicious[:30]:
            print(f"     {path}")
    else:
        check(
            "No suspicious executable-like files found in user document locations",
            True,
        )

    if scripts:
        print(
            f"     Informational: {len(scripts)} script files found in user document locations."
        )

        for path in scripts[:20]:
            print(f"     {path}")
    else:
        check(
            "No script files found in user document locations",
            True,
        )

def audit_toolkit():
    section("ISH TOOLKIT")

    expected = [
        "vault.py",
        "totp.py",
        "crypt.py",
        "shred.py",
        "ish-doctor.py",
        "ish-db.py",
        "ish.py",
    ]

    for name in expected:
        path = TOOLKIT / "tools" / name

        check(
            f"Toolkit component: {name}",
            path.exists(),
        )

        if path.exists():
            try:
                compile(
                    path.read_text(errors="replace"),
                    str(path),
                    "exec",
                )
                check(f"Python syntax: {name}", True)
            except Exception as e:
                check(
                    f"Python syntax: {name}",
                    False,
                    str(e),
                )


def audit_vault():
    section("VAULT")
    sys.path.insert(0, str(TOOLKIT))
    from lib.vault_store import VaultStore
    if not VAULT.exists():
        warn("Vault is not initialized")
        return
    if not (VAULT / "vault-v2.db").exists():
        warn("Legacy vault: explicit migration required", "Stop old clients, then run ish vault migrate.")
        return
    try:
        result = VaultStore(VAULT).check()
        check("Vault v2 metadata and integrity", result.get("integrity") == "ok")
        print("     Use ish vault verify to authenticate every encrypted record.")
    except Exception:
        check("Vault v2 metadata and integrity", False, "Run ish vault check for details.")


def audit_hashes():
    section("TOOLKIT INTEGRITY")

    tools_dir = TOOLKIT / "tools"

    if not tools_dir.exists():
        return

    for path in sorted(tools_dir.glob("*.py")):
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            print(f"{digest}  {path.name}")
        except Exception:
            pass


def main():
    print("ISH-DOCTOR")
    print("Defensive local security audit")
    print(datetime.now().astimezone().isoformat())

    audit_environment()
    audit_permissions()
    audit_startup()
    audit_processes()
    audit_network()
    audit_ssh()
    audit_documents()
    audit_toolkit()
    audit_vault()
    audit_hashes()

    section("SUMMARY")

    print(f"Checks performed : {checks}")
    print(f"Warnings         : {len(warnings)}")
    print(f"Failures         : {len(issues)}")

    if issues:
        print()
        print("STATUS: REVIEW REQUIRED")
        print("This does NOT prove the iPhone is compromised.")
        return 1

    if warnings:
        print()
        print("STATUS: REVIEW WARNINGS")
        print("No definite compromise was established.")
        return 0

    print()
    print("STATUS: HEALTHY FROM THE iSH PERSPECTIVE")
    print("This cannot certify the entire iPhone as uncompromised.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
