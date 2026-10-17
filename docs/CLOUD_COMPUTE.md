# iSH Toolkit 3.0 preview: secure compute guide

This implementation keeps the offline vault, TOTP, crypt, SQLite, workspace and
backup tools and adds an opt-in compute control plane. An iPhone can prepare
jobs, connect to an existing Linux account, inspect receipts and collect results.
It does not turn iSH into a native Linux kernel, Docker host or permanent server.

**Preview, not an independently audited security product.** Begin with dummy
data and small jobs. Your existing encrypted vault format is unchanged. No cloud
resources, SSH accounts, keys, firewall rules or billing accounts are created.

## What executes, and what does not

| Target | Implemented behavior | Boundary |
|---|---|---|
| Local | Real argv execution, timeout, cancellation request, redacted completion logs, files | Runs with your account permissions; not a sandbox |
| Existing SSH host | Strict OpenSSH connection, Python capability probe, real job execution/status/logs/files/cancel | Existing authorized account and trusted host key required |
| Remote Docker | Through the SSH endpoint, real Docker probe and restrictive `docker run` | Engine/image must already exist; no mounts, secrets, ports or automatic image pulls |
| GitHub Actions | Authenticated REST preflight/dispatch/status/jobs/cancel/log/archive download | Only the bundled reviewed `smoke` and `test` workflow contract |
| Google Cloud Shell | Primary interactive console, discovery, diagnostics, reviewed bootstrap | No permanent SSH endpoint or unattended job service implied |
| AWS CloudShell | Interactive console, discovery, identity diagnostics, bootstrap | Not an EC2 instance; region and storage constraints apply |
| Azure Cloud Shell | Interactive console, discovery, identity diagnostics, bootstrap | Ephemeral/persistent choices and possible storage charges |
| Colab | Official link and discovery-only label | No notebook automation, accelerator allocation or quota claims |

No adapter creates Compute Engine VMs, EC2 instances or Azure VMs. If you already
own an authorized Linux VM, register it through SSH. Google console access and
Compute Engine access are separate capabilities. GPU/TPU and guaranteed persistent
execution requirements currently fail closed: they are not verified by this release.

## Start with a safe local example

After installing this source using the existing `install.sh`:

```sh
ish --version
ish selftest --full
ish init
ish status
ish run --spec examples/jobs/local.json
ish run --spec examples/jobs/local.json --execute
ish jobs list
```

The first `run` only plans. `--execute` grants the exact reviewed command the
permissions of your current account, including its ability to change files or
call network services. Never run an unfamiliar command just because it appears
in a downloaded job specification. The tool cannot classify every destructive
operation or every API call that might incur charges.

Copy the returned 32-character ID, then use:

```sh
ish jobs inspect JOB_ID
ish jobs inspect JOB_ID --refresh
ish jobs logs JOB_ID
ish jobs artifacts JOB_ID
ish jobs artifacts JOB_ID --destination "$HOME/practice-download-1"
```

Replace `JOB_ID` with the actual ID. A destination must be new. Artifacts are data,
not executables to trust. A SHA-256 receipt records downloaded bytes; it is not a
signature proving that the job or remote account is trustworthy.

For a one-line command:

```sh
ish run --timeout 30 --execute -- python3 -c 'print("practice")'
```

Everything following `--` is an argument array. Wildcards, pipelines and `$HOME`
are not expanded remotely. Invoking `sh -c` explicitly is possible, but then you
are deliberately authorizing a shell program. Never concatenate untrusted input
into that program. Omit `--cwd` to use a fresh private workspace. An absolute
`--cwd` opts into an existing directory on the selected execution machine.

## Connect an existing Linux host

Prerequisites: an existing account you control, OpenSSH access, Python 3.10+ on
the endpoint, and your own verified host fingerprint. Prefer a dedicated,
unprivileged build account with no production vault, cloud keys or sudo rights.
Use a separate SSH key for this purpose. An SSH agent may unlock a protected key
locally; agent forwarding to the remote host is disabled.

Obtain the server fingerprint through an independent trusted channel, such as
the server's provider console or its administrator. Populate a dedicated
`known_hosts` file only after matching it. `ssh-keyscan` alone is not identity
verification. For a nonstandard port, the trust-file host entry uses
`[hostname]:port`. A changed key must be investigated, not bypassed.

```sh
chmod 600 "$HOME/.ssh/ish-build-key" "$HOME/.ssh/ish-known-hosts"
ish hosts add dev --address YOUR_HOST --user YOUR_USER \
  --identity "$HOME/.ssh/ish-build-key" \
  --known-hosts "$HOME/.ssh/ish-known-hosts" --existing-host
ish hosts list
ish hosts test dev
ish run --spec examples/jobs/ssh.json --allow-remote
ish run --spec examples/jobs/ssh.json --execute --allow-remote
```

`--existing-host` is your attestation that this already-existing host falls within
your approved cost budget. It does not prove the host is free. Without that
attestation, an additional `--allow-cost` is required per execution. Adding a
profile does not connect or modify the server. `hosts test` authorizes a read-only
capability probe. `hosts remove dev` removes only the profile, never a key or
remote files. Jobs retain their target snapshot for later reconciliation.

The client uses `-F /dev/null`, BatchMode, strict host-key checking, explicit
identity/known-hosts paths, no forwarding, no local command hooks and a bounded
connect timeout. It deliberately ignores `~/.ssh/config`: jump hosts, proxy
commands and interactive passwords are not supported in this preview. Use a
reachable host or arrange a trusted network/VPN separately. Never expose a
Docker socket to the internet to make a connection work.

### What happens over SSH

A fixed Python endpoint is sent as the remote command, safely shell-quoted once.
Job arguments, input bytes and authorized secret values travel as bounded JSON
on encrypted standard input, not inside the SSH command line. The endpoint uses
`Popen(argv)` with no implicit shell. It creates an exclusive job directory and
will never run the same job ID a second time.

The worker executes synchronously while the CLI waits. A second terminal can
request cancellation:

```sh
ish jobs cancel JOB_ID --confirm
ish jobs inspect JOB_ID --refresh
```

Cancellation is a request file observed by the original worker; another process
never blindly signals a saved PID. Confirmed cancellation/timeout kills the
child process group. It cannot undo completed effects, stop a daemon that
intentionally escaped the group, or guarantee completion if the worker/host was
killed. Docker cleanup is attempted by the unique container name. Inspect the
host if cleanup cannot be confirmed.

Running receipts stored on disk are historical observations. A later refresh
without a terminal receipt returns `unknown`, because no durable liveness daemon
is installed. After connection loss, do not submit a replacement until you have
reconciled the original ID. This preview never retries a submission automatically
and never silently switches provider after sending a job.

## Job specification and permissions

The version-1 input schema is illustrated in `examples/jobs/`. Unknown fields
are rejected. IDs are generated locally and saved with the validated spec,
permission record, selection explanation, target snapshot, timestamps and receipt.

| Field | Meaning |
|---|---|
| `version` | Exactly `1` |
| `type` | `command`, `docker`, or `workflow` |
| `command` | Up to 128 string arguments, each at most 4096 characters |
| `cwd` | Absolute endpoint directory, or `null` for a private workspace |
| `requires` | Optional `os`, `arch`, `full_kernel`, `gpu`, `tpu`, `persistent` |
| `resources` | Positive `memory_mb`, `disk_mb`, `cpus` requests |
| `timeout` | 1–3600 seconds; Actions rounds up to whole minutes |
| `env_refs` | Environment name to `vault:entry-name`; no plaintext values |
| `inputs` | Relative endpoint filename to absolute local input path |
| `outputs` | List of relative files to retrieve; no globbing or traversal |
| `backend` | `auto`, `local`, `ssh:NAME`, or `github` |
| `task` | Workflow-only `smoke` or `test` |
| `image` | Docker-only image pinned with `@sha256:...` |

Combined input size and downloaded artifact size are each capped at 8 MiB;
there are at most 32 input and 32 output files. Inputs require a private workspace
and never overwrite existing endpoint files. Larger transfers should use a
separately reviewed tool/workflow. Artifacts reject traversal, symlinks, hardlinks,
archive special files, duplicates, excessive expansion and existing destinations.
An interrupted download may leave a partial **new** destination; inspect it and
choose another destination for a retry. No existing directory is replaced.

`--execute`, `--allow-remote`, `--allow-secrets` and `--allow-cost` are CLI grants.
A spec cannot grant any of them. Profile presence does not grant execution.
Local/SSH resource numbers are compatibility checks against current host
observations, not reservations or cgroup limits. Concurrent processes can consume
resources after the probe. Docker explicitly enforces memory, CPU and PID limits;
ordinary commands must be trusted and run in a suitably restricted account.

States: `queued`, `submitted`, `running`, `completed`, `failed`, `cancelled`,
`timed_out`, `unknown`. `submitted` with `evidence: local-intent` records only that
a request was about to be sent. Only endpoint receipts confirm execution outcomes.
A local crash between intent and receipt can leave submitted/unknown metadata.

## Explainable scheduling

Default order is local, configured SSH hosts, then GitHub. Change it explicitly:

```sh
ish config priorities local,ssh,github
ish config show
```

The scheduler rejects targets whose measured architecture, OS, available memory,
disk or kernel capabilities do not meet the request. Unknown required values are
rejected. Remote probes only happen with `--allow-remote`. Unreachable targets can
be skipped **before submission**; submitted work is never retried elsewhere.
Explicit `--backend ssh:dev` limits selection to that host and overrides the spec.

Cloud consoles cannot be selected for unattended jobs. Their session availability
and remaining quota are not inferred from an installed CLI. GitHub runs only its
fixed workflow tasks, with exact contract preflight after authentication. Its
quota/cost are unknown during planning, so `--allow-cost` is mandatory. There is
no false dollar estimate. Input transfer is bounded rather than forecast using
an invented bandwidth estimate. This is a deterministic explainable scheduler,
not an AI or an autonomous resource-provisioning service.

## Secrets and log safety

A job may declare, for example, `"env_refs": {"SERVICE_TOKEN": "vault:dev-token"}`.
Use the existing hidden-input `ish vault set dev-token` flow to store the value.
Execution additionally requires `--allow-secrets`. The master password is prompted
locally and never sent to a provider. Only the selected secret values are sent
in SSH's encrypted input and delivered to the authorized child environment.
The environment strips ambient AWS/Azure/GitHub credentials, loader variables,
SSH agent sockets and other shell environment values. Local PATH/HOME are still
needed for execution, and the running account can read its own files.

**Remote execution trusts the remote account and workload.** Host administrators,
malicious job code and same-account processes can access delivered values. A
private workspace is not an isolation boundary. Do not send production secrets
to an unfamiliar host, a general notebook or a cloud console merely because the
transport is encrypted. Docker jobs in this preview reject secret environment
references and host mounts altogether.

Worker output is drained with a bounded capture buffer (about 1 MiB), literal
secret values are removed before persistence, common token forms are masked, and
terminal control characters are escaped. Capture truncation drops a guard region
to avoid persisting a partial secret at the size boundary. Logs appear after
completion, not live. A crash can lose the in-memory log buffer.

Redaction cannot detect every secret, transformed/encoded values, or credentials
hard-coded in arguments or files. Never put passwords/tokens in the job command,
job JSON, shell history or output artifacts. Arguments and source paths are stored
as metadata. Artifacts are not automatically redacted. GitHub also applies its own
masking; configure workflow secrets there and never echo them. The bundled tasks
do not request production credentials.

## Google Cloud Shell: primary interactive path

```sh
ish cloud google status
ish cloud google open
ish cloud google doctor
ish cloud google setup
```

`status` is offline: it checks CLI/config presence and an environment hint. A hint
is explicitly **not** authenticated proof of a Cloud Shell session. `open` prints
only the official browser URL, https://shell.cloud.google.com/. It does not create
an execution connection. `doctor` checks HTTPS reachability and the official
CLI's active-account configuration without printing account details or tokens.
Google's cached active account is reported as configured, not API-authorized.

Inside a user-authorized console, clone and inspect the repository before running
its user-space bootstrap:

```sh
git clone https://github.com/braze222/ish-toolkit.git "$HOME/ish-toolkit-cloud"
cd "$HOME/ish-toolkit-cloud"
git log -1 --oneline
# Review scripts/bootstrap-cloud.sh and the source at the chosen commit.
sh scripts/bootstrap-cloud.sh
export PATH="$HOME/.local/bin:$PATH"
ish status
ish selftest --full
```

The bootstrap checks origin and a clean checkout, requires Git/Python, creates a
project `.cloud-venv`, installs runtime dependencies there and uses the existing
launcher installer. It uses no sudo, global pip or resource API. Rerunning keeps
user data and uses the same reviewed checkout; it does not silently pull new code.
For an update: fetch, review the diff, then perform an explicit fast-forward and
rerun the bootstrap. Preserve uncommitted changes first. Package downloads require
network access; local tools remain offline-capable after installation.

Google home persistence depends on the chosen mode. Runtime state and processes
are temporary; inactivity, session and account quotas apply. Check current usage
in the provider's console. Never use keepalive automation to evade quotas. For
unattended Google workloads, explicitly register an existing authorized Linux VM
via SSH or use a reviewed Actions task; the toolkit provisions neither.

## AWS and Azure interactive paths

```sh
ish cloud aws status
ish cloud aws open
ish cloud aws doctor
ish cloud aws setup
ish cloud azure status
ish cloud azure open
ish cloud azure doctor
ish cloud azure setup
```

The official URLs are https://console.aws.amazon.com/cloudshell/ and
https://shell.azure.com/. Authenticate through the provider, retaining MFA.
The doctor uses `aws sts get-caller-identity` or `az account show`, discards identity
output and reports only success/failure. AWS failures may be authentication,
network, region or policy-related. Azure account information can be cached; it
is not proof of permission to create resources. Configuration presence alone
never means authentication succeeded.

AWS storage is region-specific and VPC environments have different persistence.
Azure offers ephemeral sessions and persistent Azure Files choices; the latter
can incur storage charges. A subscription/account may need setup by its owner.
The same reviewed user-space bootstrap is usable in a suitable Linux console;
actual provider sessions have not been exercised in this build environment.
Do not provision storage or compute automatically to resolve a failed doctor.

## GitHub Actions setup

Use a repository you control, with the reviewed `.github/workflows/ish-job.yml`
present on its default branch and at your chosen branch/tag. Review the **whole
source revision**, because the test task executes repository tests. The adapter
compares the workflow contents byte-for-byte with its installed contract and
requires the configured ref to resolve to your reviewed commit.

Authenticate using either `gh auth login --hostname github.com` through the
official GitHub CLI, or a fine-grained token entered privately into the vault.
Limit the token to the selected repository, Actions read/write and Contents read
(for source verification). It needs no administrative permission, account-wide
scope or cloud credentials. The toolkit never reads browser cookies or bypasses MFA.

```sh
ish config github --repo OWNER/REPO --ref YOUR_BRANCH_OR_TAG --commit FULL_REVIEWED_SHA
# Or append --token-ref vault:github-actions after storing that token privately.
ish run --spec examples/jobs/github-smoke.json --allow-remote --allow-cost
ish run --spec examples/jobs/github-smoke.json --execute --allow-remote --allow-cost
ish jobs inspect JOB_ID --refresh
ish jobs logs JOB_ID
ish jobs artifacts JOB_ID
ish jobs artifacts JOB_ID --artifact-id ARTIFACT_ID --destination "$HOME/actions-result-1"
```

The documented dispatch API accepts a branch/tag; the commit is checked separately.
The bundled workflow guards its execution against a moved ref and checks out the
reviewed commit. Repository writers can change workflows: protect refs and restrict
write access. This is not protection against a compromised repository administrator.
The API's returned run ID is retained when provided; otherwise the adapter searches
the latest 100 dispatches for a unique matching ID and commit. An ambiguous or lost
response produces `unknown`, never a second dispatch. Older/higher-volume runs
may require manual inspection in GitHub. Rate-limit and auth errors are reported
without response bodies, tokens or signed download URLs.

`smoke` compiles source and prints the version. `test` installs test dependencies
and runs the suite. Workflow inputs never become interpolated shell commands.
Actions are pinned by commit, checkout credentials are not persisted, workflow
permissions are read-only, time is bounded and artifacts retain for one day.
No arbitrary shell, self-hosted runner label, custom workflow or resource creation
is accepted by this adapter. Downloaded ZIPs are bounded and validated before
extraction; the API credential is never forwarded to signed storage URLs.

Public standard-runner eligibility differs from private plan allowances, larger
runners and artifact storage. Remaining quota is not available from this generic
adapter; review your account usage and budgets before granting cost permission.
No claim of universally free compute is made. GitHub dispatch/account integration
is unit-tested with mocked APIs here; live authenticated CLI dispatch still needs
an authorized account test. Repository CI runs are separate evidence.

## Docker on an existing remote host

```sh
ish hosts test dev --docker
```

The probe runs `docker info` over verified SSH and requires a Linux engine. A
`type: docker` spec must select that host, use a digest-pinned image already
present on it, and provide command arguments. Defaults: no network, read-only
root filesystem, dropped capabilities, no-new-privileges, nobody UID/GID,
128-PID limit, 256-MiB memory, one CPU and a 64-MiB noexec temporary filesystem.
Memory/CPU can be requested in the spec. No host mounts, privileged mode, socket
mounts, ports, environment secrets or automatic image pulls are supported.

Images must still be trusted. Docker daemon access is a powerful host privilege;
use a dedicated rootless-compatible setup when practical. This release's Docker
command/security assembly is tested with a process double, not a real engine.

## Operations, recovery and uninstall

Configuration and local job metadata: `~/.ish-toolkit/compute/` (700 directories,
600 files). Endpoint receipts/workspaces/logs: `~/.ish-toolkit/compute-endpoint/`
on the execution account. These paths contain plaintext metadata and possibly
job outputs. Do not commit them or include them in public issue attachments.

The installer does not initialize/migrate your vault or edit compute configuration.
Keep the prior source folder and launcher backup for rollback. Reinstalling the
previous source restores old launchers while retaining newer compute state.
Older tools simply do not understand the new commands. Do not manually edit a
live job record to make an uncertain job look successful.

To stop using compute: finish/reconcile jobs, remove unused host profiles, revoke
or rotate dedicated credentials with the relevant provider, and remove launchers
only after checking where they point. Deleting a host profile does not stop jobs
or revoke keys. No uninstall command silently deletes vaults, SSH keys, backups
or endpoint workspaces. Remove obsolete dummy-data directories manually only
after checking their contents. See UPGRADE.md for the older launcher rollback.

| Symptom | Next step |
|---|---|
| Unknown command | Check `ish --version`, PATH and source-folder launcher target |
| SSH transport failed | Verify network, account/key, independently confirmed fingerprint and endpoint Python |
| Job unknown | Refresh original ID; inspect host/Actions; never immediately resubmit |
| Resource rejection | Reduce requirements or configure a verified suitable host |
| Missing logs | Worker publishes sanitized logs at completion; a crash may lose them |
| Artifact rejected | Check relative paths, regular files, 8-MiB limit and new destination |
| GitHub workflow mismatch | Review/update both installed and remote contract intentionally |
| Ref moved | Review new commit and reconfigure; do not waive verification |
| Permission error on iSH lock | Another operation may hold it; do not remove fail-closed locking |
| Filesystem/system-call failure | Stop; preserve data; report dummy-data reproduction and device version |

## Documentation registry and verification

Reviewed on 2026-10-16; these are documentation observations, not account quota
measurements. Recheck periodically and before changing encoded assumptions.

- Google limits: https://docs.cloud.google.com/shell/docs/quotas-limits
- Google behavior: https://docs.cloud.google.com/shell/docs/how-cloud-shell-works
- AWS limits: https://docs.aws.amazon.com/cloudshell/latest/userguide/limits.html
- Azure overview: https://learn.microsoft.com/en-us/azure/cloud-shell/overview
- Azure ephemeral: https://learn.microsoft.com/en-us/azure/cloud-shell/get-started/ephemeral
- Actions billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- Dispatch contract: https://docs.github.com/en/rest/actions/workflows
- Run status/cancel/logs: https://docs.github.com/en/rest/actions/workflow-runs

No fixed free-hour, storage allowance or session-lifetime promise is encoded.
See COMPUTE_VALIDATION.md for the exact test evidence and remaining limits.

Artifact ZIP members must use stored or deflate compression. Other codecs,
malformed members and CRC failures are rejected before any files are published.
