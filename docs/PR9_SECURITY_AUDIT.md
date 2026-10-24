# PR9 security and reliability audit — 23 October 2026

Status: preview changes under review, not a zero-risk or production certification.

## Baseline and scope

PR9 baseline `1b698ba227cc61a535b77b0470fdef9f2ce5cc4c`, plus the owner's uploaded six-file patch and four new scripts/tests. The subsequent init-scope fix, absent-launcher rollback case and zero-discovery gate were reconstructed from the reviewed conversation. No iPhone installation or private data was accessed. A fresh checkout was used; existing worktrees were preserved.

Specialist agents were requested but hit an environment usage limit. Findings and implementation were completed by the lead agent; this is not an independently completed multi-person security audit.

## Changes and threat boundaries

- `elmatrix-standalone/elmatrix/transport.py`: feed DNS is resolved once for each hop, every address must be public, then the socket connects to that exact address. HTTPS uses the original hostname for certificate verification/SNI. Environment proxies are not used; redirects are bounded and HTTPS downgrades rejected. Responses are byte bounded and compressed responses refused. Network errors omit URLs/query tokens. No remote workload or paid API was used.
- `evidence.py`: preserve Atom timestamps, select alternate Atom links, reject DTD/entity declarations and NUL-encoded XML; IPv6 URL formatting and control-character checks. SQLite uses owner-only permissions, refuses symlink/hardlink destinations and unsafe sidecars, rejects future schema versions without migration. Existing version1 data is preserved.
- `server.py`: loopback binding, exact Host and Origin checks, query limits, safe link schemes, no-store responses. Serial serving avoids unbounded thread creation. Source text remains rendered using textContent.
- `cli.py`: fix local `os` import breaking init; close experiment connections and validate opportunity IDs; clean storage failures. Exports use exclusive hard-link publication and do not replace existing destinations. Hard-link support is required: export locally then copy to Files if mounted storage does not support it.
- `engine.py`: user fit only, with seeded market assumptions separate; fix case mismatch for ZA; reject invalid budgets/hours. Scores remain heuristics, not measured demand.
- `scripts/install.py`: preserved rollback fixes, recovery backups, absent-file restoration and preflight source/type checks. Does not initialize a live vault.
- `tools/ish-selftest.py`: artifact coverage restored by default. `--skip-artifacts` is explicit and rejected with `--full`. Quick verifier uses control plus skip; full verifier exercises full self-test. Skipped coverage is printed.
- Both verifier scripts propagate failures. Standalone zero-test discovery fails; regression fixtures run the actual verifier with empty/failing/passing suites.
- Standalone CI actions pinned to the repository's existing immutable pins; installed CLI smoke runs outside the source directory.

## Verification commands

```sh
# Linux development environment with requirements-dev.txt installed
python -m pytest -q tests
(cd elmatrix-standalone && python -m unittest discover -s tests -v)
python tools/ish-selftest.py --full
python scripts/check_secrets.py
```

On iSH use `python3 tools/ish-verify.py --quick` first. Do not repeatedly retry a known SIGSYS failure. The owner's previous 19 standalone and 6 installer test passes are separate from Linux verification of this newer code.

## Residual risks and uncompleted gates

- Intermittent iSH SIGSYS remains unexplained. Later passes did not prove a fix. New transport/database changes require device verification; no all-iPhone compatibility claim.
- OS DNS resolution and slow-response behavior are not protected by a strict overall wall-clock deadline. Socket timeouts and byte/redirect limits are bounds, not complete denial-of-service protection.
- Dashboard is local single-user software, without authentication; local programs can read it and slow local clients can delay service. Never bind/publicly proxy it as a hosted multi-user service.
- Database checks do not defend against a malicious process running as the same OS user racing filesystem operations. Evidence is not encrypted. Do not place secrets in observations or feed URLs.
- Installer rollback handles caught failures, not power loss; concurrent installs are unsupported. Retain backups. No destructive cleanup is provided.
- Human reviews and freshness hints do not establish independent corroboration or commercial viability. No AI inference, publishing or revenue automation was added in this audit.
- Broad dependency ranges resolve differently over time; dependency scans are point-in-time checks. Pattern scanning cannot prove absence of secrets.
- No release has been merged or published. Do not pull over the owner's uncommitted checkout. Preserve/stash/commit those changes before integrating this branch.

## Local audit evidence

Python3.12 Linux: complete toolkit pytest suite205 passed,2 optional SSH tests skipped. standalone unittest suite30 passed; installer rollback6 passed; actual verifier empty/failure/success fixtures3 passed. Full isolated self-test passed including artifacts and vault crypto/recovery. Installed wheel version0.4.0 passed version/init/niches/report from a temporary working directory outside the repository. `pip-audit -r requirements-dev.txt` reported no known vulnerabilities; includes runtime requirements. Secret pattern scanner checked126 tracked files/blobs with zero pattern findings. These are limited checks, not a security guarantee.
