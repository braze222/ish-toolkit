# 3.0 preview validation record

Build-host checks performed 2026-10-16 UTC (2026-10-17 in South Africa).
This is implementation evidence, not a security certification or independent audit.

## Executed checks

| Check | Observed result |
|---|---|
| Unmodified 2.1.1 baseline, Python 3.12 | 120 tests passed |
| New compute and loopback SSH tests | 46 tests passed |
| Full suite with `ISH_TEST_SSH=1` | **167 tests passed in 55.13 seconds** |
| Installer + compute regression subset | 46 tests passed |
| Final default-config/help CLI regression | 1 test passed |
| Expanded `ish selftest --full` | Passed, including local job/log/artifact retrieval, vault rotation, backup recovery and protected keys |
| Python compile + shell syntax | Passed for source/tests, installer and bootstrap |
| Workflow YAML parse | All three workflow files parsed |
| Tracked-source common-secret-pattern check | No pattern findings; limited regex coverage |
| `pip-audit -r requirements-integration.txt` | No known vulnerabilities in the resolved optional test dependencies |

The runtime dependencies were not changed by this feature. The repository security
workflow audits runtime, development and optional integration dependencies; its
results must be checked for the published commit. This record does not predeclare
that a future CI run passed. See the repository Actions page for actual run IDs,
Python 3.10/3.12/3.13 results and security-workflow outcomes.

## What the real SSH test did

An actual OpenSSH client connected over TCP to a temporary loopback SSH server,
authenticated with a disposable generated key, checked a pinned temporary host
key, sent the exact endpoint program/request, and executed a Python command in
an isolated endpoint HOME. The test retrieved its terminal receipt, redacted log,
and output file and verified the output contents. A deliberately incorrect server
key was rejected. All listeners, keys and test files were temporary; no user host,
SSH key, provider account or vault was used.

The server used optional Paramiko 5.0.0 as a userspace test fixture. An initial
native sshd attempt could not use its required chroot in the build container, so
it was not counted as a passing native-server test. The userspace fixture requires
no privileged server setup and only accepts the exact reviewed endpoint command.
This establishes a real SSH protocol round trip, **not** remote cloud deployment,
production OpenSSH-server coverage or an iPhone device result.

## Mocked or unexercised paths

- GitHub API preflight, dispatch receipts, failure/rate-limit handling, token-safe
  errors and archive redirect boundaries are tested with API doubles. No live
  authenticated dispatch was available through this build session's connector.
  Push-triggered repository CI is separate from a CLI-dispatch integration test.
- Docker command security flags are tested with a real child-process double of
  the Docker executable. No actual Docker engine/image was available for this run.
- Google/AWS/Azure discovery and failure handling are tested with controlled
  environments and CLI/network doubles. Their actual interactive accounts and
  bootstrap sessions were not exercised.
- The new runtime has not been run on the user's iSH device. The previously
  observed v2.0 device self-test does not validate 3.0. Run the expanded full
  self-test on iSH before real data/remote credentials.
- No native GPU/TPU or persistent-daemon execution is advertised. Required
  capabilities that cannot be verified are rejected.

## Reproduce

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
# Optional real loopback transport check on a Linux host with OpenSSH client:
python -m pip install -r requirements-integration.txt
ISH_TEST_SSH=1 python -m pytest -q tests/test_compute_ssh.py
python tools/ish.py selftest --full
python scripts/check_secrets.py
```

The regular suite skips the two opt-in SSH integration tests. The Python 3.12 CI
job installs the optional fixture dependency and runs those two separately.
External provider tests require your own explicitly authorized environment and
cost review. Do not paste real tokens, passwords or private keys into test reports.

## Remaining release gates

Before treating the preview as a stable supported release: validate on iSH,
exercise authenticated GitHub dispatch/log/artifact/cancellation end-to-end,
exercise real Docker cleanup and representative OpenSSH Linux hosts, test the
bootstrap in each console, and obtain independent security review. Repository
account MFA, protected refs, private vulnerability reporting and push protection
remain owner-admin settings; this code change does not claim they were enabled.
