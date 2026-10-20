# Elmatrix research preview — independent of iSH Toolkit

Elmatrix 0.1.0-preview is a small, Python-standard-library research CLI. Its first
job is to gather public YouTube observations and help you decide what to research
next. It is not a revenue engine or a video generator. Existing `ish` commands,
vaults, compute settings and launchers are not modified by its installer.

## Install / automatic deployment

From an updated checkout of this repository:

```sh
sh install-elmatrix.sh
export PATH="$HOME/.local/bin:$PATH"
elmatrix --version
elmatrix providers
```

Requires POSIX (Linux/iSH), working Python 3.10+ and `python3` on PATH. No pip,
OpenCode, paid API or crypto dependencies are required. This does not certify every
iPhone generation. If needed, set `ELMATRIX_PYTHON` for the build; the installed
zipapp uses `python3` on PATH, which the installer checks before replacement.

Deployment builds a self-contained `dist/elmatrix/elmatrix.pyz`, smoke-tests it,
then atomically installs only `~/.local/bin/elmatrix`. A previous Elmatrix command
is backed up under `~/.local/bin/elmatrix-backup-*`. The source directory can be
moved after installation; it is not needed to run the zipapp. To roll back, copy
the saved `elmatrix` executable over the current one. Research data is separate.
The SHA256SUMS file detects accidental corruption; it is not a publisher signature.

Every push to main automatically runs the toolkit test matrix. On Python 3.12,
it also builds, installs and smoke-tests Elmatrix and uploads the deployment bundle
as `elmatrix-<commit>` in the Actions run (retained seven days). Download from a
successful run, verify the checksum, and run `python3 elmatrix.pyz --version`.
This is automatic CI packaging/deployment verification, **not remote installation
on your phone, an always-on server, or a hosted service**. No hosting target or
server credentials have been supplied. The local installer is the actual device
deployment step; no unattended self-updater replaces a working installation.

## Start offline without a key

```sh
elmatrix scan --niche cleaning --input examples/elmatrix/demo-videos.json
elmatrix report
elmatrix trends
```

The example is **fictional demo data**, not a real market result. Imports accept a
YouTube `videos.list` JSON object with `items`, `id`, `snippet` and `statistics`.
They are marked `imported-unverified` and are never mixed with live observations.
Imported timestamps mean import time; they do not certify when exported data was
actually collected. Delete the demo before real research if desired:

```sh
elmatrix purge --all
```

This deletes only Elmatrix's stored snapshots, not anything on YouTube.

## Live YouTube scans

Enable the official YouTube Data API for your Google project and create a restricted
API key. In an interactive terminal, Elmatrix prompts for a key without echoing or
saving it:

```sh
elmatrix scan --niche services
elmatrix scan --niche cleaning --query 'cleaning business South Africa' --region ZA
elmatrix scan --niche repairs --query 'plumbing maintenance' --limit 20 --days 14
```

For unattended use, supply `YOUTUBE_API_KEY` through your host's secret environment.
Never put it in source, shell history or screenshots. The key is sent in a header
to the fixed Google API host; redirects are rejected, and raw provider errors are
not printed. Access/quota failures stop the scan, with no hidden retries.

Each live scan makes one bounded `search.list` request (date ordering by default), followed
by at most one `videos.list` request. No scraping, downloading videos or pagination
loops. Your project's quota and terms apply; Elmatrix does not inspect billing,
create cloud resources or fall back to paid AI. A quota-limited API is not unlimited
free access. Missing/private/deleted results may be omitted by YouTube.

Use `--order viewCount` for YouTube's own view-count ordering, or `--order relevance`
for its relevance ordering. These do not establish profitability or channel quality.

Presets: `services`, `cleaning`, `repairs`, `beauty`, `tutoring`, `automotive`,
`digital-services`, `kids`. `--query` lets you research any other niche.
`--channel UC...` restricts a scan to a specific channel ID. `--region` is a YouTube
regional search context, not proof of a creator's location. Strict SafeSearch is
requested for all scans; it is not a child-suitability certification.

## Bounded autonomous collection

```sh
elmatrix scan --niche digital-services --cycles 7 --interval 86400
```

This runs seven foreground scans one day apart. The minimum interval is one hour;
maximum cycles is 24 per invocation. Ctrl-C stops it. Any failed scan stops the
loop. An always-on Linux host is needed for reliable unattended operation: iOS can
suspend iSH, and this command does not bypass that. It has no hidden daemon,
restart/retry loop, scheduled cloud job, upload or spend permission.

## Trends and reports

```sh
elmatrix trends --niche cleaning --history 7
elmatrix report --niche cleaning
elmatrix report --format json
elmatrix report --format opencode
```

`trends` shows raw historical observations for the latest matching query, source,
region, channel, source ordering, time window and sample limit. One scan is a baseline, not a trend.
A repeated search may return different videos; it is not a census of a niche.
Views/likes/comments are the source's counts, with missing counts shown as unknown.
No custom growth score, derived RPM, revenue estimate or best-channel ranking is
calculated. This avoids representing estimates as facts and respects the public
API's restrictions on derived metrics.

Actual competitor earnings and monetization status are unknown. Owner-authorized
YouTube Analytics would be a separate future integration; it cannot reveal other
creators' private earnings. An original service-business lead-generation concept
or an original children's lesson can be a research goal, but revenue is not assured.

## OpenCode and free-provider discovery

```sh
elmatrix providers
elmatrix providers --refresh
elmatrix report --format opencode > research-brief.md
```

The default provider check is offline: it reports whether OpenCode is on PATH and
whether a YouTube key is present, without reading OpenCode credentials or validating
access. `--refresh` fetches the public Models.dev catalog also used by OpenCode and
lists models with explicit zero input **and** output token prices. Missing pricing
is never treated as free. Catalog zero prices are candidates only: rate limits,
account eligibility, geography, other charges and provider privacy terms may differ.
The catalog timestamp and source are shown; no hardcoded promise of free models.

The OpenCode integration in this first release is **catalog discovery and an explicit
research brief handoff**, not automatic agent execution. Review the generated brief
and use your separately installed OpenCode to inspect it if you choose. Its documented
`opencode models --verbose` command exposes model/cost metadata. Do not pass untrusted
video titles as shell commands. Elmatrix does not run `opencode run`, auto-approve
tools, transmit research to an AI provider, generate videos or upload to YouTube.
OpenCode itself may not run on iSH's architecture; Elmatrix still works independently.

Future content work should produce original scripts, characters, visuals, music and
voices with appropriate rights, and require review before publication. Researching
successful channels is not permission to copy their videos or impersonate them.

## Local data and retention

Snapshots are plaintext research data under `~/.elmatrix` (0700 directory, 0600
files), separately from toolkit/vault data. Set `ELMATRIX_HOME` to change this path.
Kernel locks and atomic exclusive publication prevent overlapping writes; unsafe
symlink paths fail closed. No API key or raw API response is persisted.

Stored snapshots aged 29 days are deleted when scan/report/trends runs. This is a
conservative margin under YouTube's 30-day public-data storage limit. An inactive
process cannot delete files while your phone is off: run `purge --all` when retiring
the tool, and arrange regular maintenance on an always-on host. You must also delete
or refresh exported reports/backups within the applicable period. `providers` does
not touch research storage. No content is uploaded by this tool.

## Verification and limits

Automated tests cover offline workflows, provider response validation, failure/no
partial snapshot behavior, key exclusion, retention, separate queries, symlink
rejection, no-redirect behavior and independent install/reinstall. The full toolkit
suite checks for regressions. Live YouTube access requires your key; no live scan or
OpenCode inference is claimed based on fixtures. There is no independent security
audit, monetization certification, universal iOS support or deployed hosted service.

Official references (reviewed 2026-10-20):
- https://developers.google.com/youtube/v3/docs/search/list
- https://developers.google.com/youtube/v3/docs/videos/list
- https://developers.google.com/youtube/terms/developer-policies
- https://opencode.ai/docs/cli/
- https://models.dev/

Local verification on 2026-10-20: the initial combined suite passed 194 tests
including loopback SSH; the final Elmatrix-only suite passed 17 tests after three
additional credential/deployment regressions were added (197 distinct test cases
overall). Live Models.dev discovery returned candidates successfully. Standalone
bundle build and offline execution passed. Bandit 1.9.4 found zero high/medium
findings and four low subprocess warnings in the intentional deployment smoke
checks; none were suppressed. GitHub Actions records the combined final result.
