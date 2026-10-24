# Elmatrix video pilot

A separate, explicit workflow: original script starter → your cover and narration →
portrait MP4 → private YouTube upload. Existing `elmatrix scan`, vault and toolkit
installation are untouched. This is a manually operated pilot, not an autonomous
AI generator, scheduler, monetization system or production release.

## iSH: use the browser-rendering path

The reported Alpine x86 FFmpeg and ffprobe both terminate with SIGSYS (exit 159)
on this iSH device. Reinstalling the same binaries is not a compatibility fix.
Local rendering is now refused when the kernel identifies as iSH, before launching
native media tools. `doctor` does not execute them. Existing packages are not removed
or changed by these commands.

This path needs only Python's standard library in iSH and a Google Colab session in
the iPhone browser. It does **not** require another computer, SSH, a paid AI API,
YouTube OAuth or uploading credentials. It is an interactive handoff, not unattended
remote execution. Colab's free resources are limited and not guaranteed.

```sh
cd "$HOME/elmatrix-video-pilot"
git pull --ff-only origin feature/video-pilot
python3 video-pilot/elmatrix_video.py doctor
python3 video-pilot/elmatrix_video.py prepare-cloud \
  "$HOME/elmatrix-videos/cleaning-001" \
  --output /mnt/xxix-share/cleaning-001-job.zip
```

`prepare-cloud` exports only schema, title, description and script. It does not copy
API keys, vault contents, arbitrary extra metadata or other project files. Inspect
the script before uploading it: those selected fields will be sent to Google Colab.
The destination ZIP must not already exist.

Open [the Colab notebook](https://colab.research.google.com/github/braze222/ish-toolkit/blob/feature/video-pilot/video-pilot/Colab_Render.ipynb)
on the iPhone, sign in, select a **CPU** runtime and run the cells in order. The setup
cell installs dependencies in the cloud VM, not on the phone. When prompted, select
`cleaning-001-job.zip` from xxix in Files. The notebook embeds its renderer code
rather than downloading executable scripts from unpinned URLs.

It creates an original title card and generic synthetic English narration with
espeak-ng, then a portrait MP4. It requires no supplied image or microphone recording.
This is a simple narrated-card draft, not AI-generated footage or a cloned voice;
review voice quality, pronunciation, spelling and usefulness. The first version
accepts ASCII English title/script text, with script at most 2000 characters and
rendered audio at most 180 seconds. Edit the project to improve the result; no AI
writing provider is invoked. Your script controls the narration.

Preview the video in the notebook, download `render-result.zip` and save it to xxix.
Then run in iSH:

```sh
python3 video-pilot/elmatrix_video.py import-render \
  "$HOME/elmatrix-videos/cleaning-001" \
  --bundle /mnt/xxix-share/render-result.zip
```

The importer checks fixed archive names, bounded sizes, project identity, the video
hash and MP4 header without invoking ffprobe. It rejects existing renders, symlink
destinations, duplicate archive entries and path traversal. Hashes detect mismatches;
they do not authenticate the renderer or prove a video is safe to open. Import only
the result you created. Play the MP4 using the iPhone's native player or notebook.
The file remains under the project directory; you can copy it to Files for viewing.

Neither export, notebook rendering nor import uploads to YouTube. For an iPhone-only
first publication, review and upload using the official YouTube app. The separate
OAuth CLI upload remains unverified on iSH; do not treat the cloud renderer as a fix
for all iSH subprocess/OAuth failures. No monetization eligibility is established.

If interrupted, rerun the notebook with the same input bundle; it uses a new temporary
workspace each time. That can repeat rendering but never posting. Failed import may
leave a video without metadata after a filesystem failure; keep the project and use
a new project directory instead of deleting state blindly. The cloud VM is temporary:
download your result before ending the session. Files are not automatically saved to Drive.

Google's availability policy: https://research.google.com/colaboratory/faq.html

## Requirements and installation

Python 3.10+, FFmpeg/ffprobe with libx264 and AAC, and (for upload only) the Python
packages in requirements.txt. Render on a computer first. Local iSH rendering is disabled; use the browser path above. OAuth
browser handoff on iSH has not been validated. Do not treat Linux tests as iPhone support.

From this repository's root:

```sh
python3 -m venv video-pilot/.venv
video-pilot/.venv/bin/python -m pip install -r video-pilot/requirements.txt
python3 video-pilot/elmatrix_video.py --help
```

Install FFmpeg using your operating system's package manager. The code checks for
both ffmpeg and ffprobe. It neither installs packages nor charges a generation
provider automatically.

## Make your first video

Keep projects OUTSIDE the git checkout. The following commands are for a POSIX
terminal (Linux, macOS or iSH); the project parent must already exist.

```sh
mkdir -p "$HOME/elmatrix-videos"
python3 video-pilot/elmatrix_video.py init "$HOME/elmatrix-videos/cleaning-001"
```

Open `project.json`: review the original example script, title and description.
Adapt them with useful, accurate information. Record the script in your own voice
and save as WAV, MP3 or M4A (1–180 seconds). Create an original portrait cover
(PNG/JPEG); keep licenses/permission for any third-party material. The script field
is a planning aid: editing it DOES NOT regenerate narration or captions.

```sh
python3 video-pilot/elmatrix_video.py render "$HOME/elmatrix-videos/cleaning-001" \
  --image "$HOME/elmatrix-videos/cover.png" \
  --audio "$HOME/elmatrix-videos/narration.wav"
```

This creates `video.mp4` and `render.json` (hashes and duration). It is a single
still-image video with audio, 720×1280 H.264/AAC; no scene generation, stock search,
music or captions are included. Use trusted media. Watch the whole MP4, listen to
the narration and check metadata. Existing renders are never overwritten; create a
new project for revisions. A repeated template is not a monetization strategy.

## Authorize your channel and upload privately

1. In Google Cloud, enable YouTube Data API v3 for your project, configure the OAuth
   consent screen and add your account as a test user if the application is in testing.
2. Create an OAuth **Desktop app** client and download its JSON. Keep it outside
   the repository, e.g. `$HOME/.config/elmatrix-video/client.json`, with mode 600.
   Your existing research API key cannot authorize an upload.
3. Get your exact YouTube channel ID (`UC` followed by 22 characters).
4. Run the command below after reviewing the complete video and confirming rights.
   Replace the example channel ID. Choose audience and synthetic-media declarations
   accurately; `general` means not made for kids and is NOT an age restriction.
   `--synthetic` refers to YouTube's altered/synthetic content disclosure, not simply
   whether an AI assisted with writing.

```sh
video-pilot/.venv/bin/python video-pilot/elmatrix_video.py upload \
  "$HOME/elmatrix-videos/cleaning-001" \
  --client-secrets "$HOME/.config/elmatrix-video/client.json" \
  --channel UC_REPLACE_WITH_YOUR_CHANNEL_ID \
  --audience general --synthetic no --confirm-reviewed
```

Open the authorization URL printed by Google's library in a browser **on the same
computer/device running the command**. The temporary callback listens on loopback
only for up to five minutes. This is not a headless-server authentication recipe.
Do not send the URL, client JSON, passwords or tokens to chat. The tool uses PKCE,
requests upload plus read-only scopes (to check channel identity), and keeps OAuth
tokens in memory only. It asks for authorization each time. Revoke app access in
your Google account whenever needed.

The authorized channel must match exactly. Uploads always request private visibility
and disable subscriber notifications. No public publishing command exists. Review
processing, copyright checks and audience declarations in YouTube Studio. A receipt
means the API returned a video ID; it does not mean processing or monetization passed.
API project restrictions may prevent public publication; changing the client code
cannot bypass those restrictions.

## Recovery and limits

`upload-attempt.json` is exclusively created before the upload network request.
Any subsequent upload from that project is refused, including after interruption.
An uncertain upload must be checked in Studio first; there is intentionally no
automatic retry/reset command. A lost final response can mean the video exists
without a local receipt. Preserve the marker and reconcile manually. This prevents
blind retries per project, not duplicates across copied projects, users or machines.
No cross-process adversarial sandbox or power-loss transaction guarantee is claimed.

Resumable upload chunks are used within one process. Restart/resume across process
failure is not implemented. Provider failures are reported without response bodies
or token-bearing URLs. OAuth client files must use official Google endpoints.
Network timeouts do not prove universal iSH syscall compatibility. No live account
upload has been tested by the implementation author.

## Verification

```sh
python3 -m unittest discover -s video-pilot/tests -v
python3 video-pilot/tests/render_smoke.py
```

Tests use temporary projects and mocked YouTube services, never your credentials.
The smoke test uses generated test media and requires FFmpeg; it verifies a real
MP4 has audio/video and that existing output is not overwritten.

Official references:
- https://developers.google.com/youtube/data/guides/uploading_a_video
- https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
- https://googleapis.dev/python/google-auth-oauthlib/latest/reference/google_auth_oauthlib.flow.html

## Hugging Face / Arena: script drafting handoff

Checked 2026-10-24. This pilot integrates **manual prompt export and validated JSON
import**, not automated inference on either provider. These commands use only Python's
standard library: no native AI runtime, token entry, website scraping or API request.

Current Hugging Face Inference Providers pricing lists **no included monthly credits
for free accounts**. Earlier descriptions of $0.10 free credits are stale. API use
requires purchased credits or an eligible subscription. Model weights being public
is not the same as free hosted inference, or permission to use every model commercially.
Review the license of a model before building it into a production pipeline.

Arena documents API integrations for OpenCode and other clients, but its Claude Code
docs state that **free-router keys work in Claude Code only**. This is not evidence
of a free general-purpose API for Elmatrix. Workspace API rights may differ. We do
not impersonate approved clients, bypass key restrictions or call website internals.
Website/model availability and usage limits must be checked in your own account.

The useful first integration is original script drafting for the cleaning/service
niche. It works with either website and feeds the existing cloud-rendering workflow.

```sh
python3 video-pilot/elmatrix_video.py providers
python3 video-pilot/elmatrix_video.py ai-prompt \
  "$HOME/elmatrix-videos/cleaning-001" \
  --provider arena --niche 'cleaning services' \
  --audience 'South African adults comparing local cleaning services' \
  --output /mnt/xxix-share/cleaning-ai-prompt.txt
```

Choose `--provider huggingface` instead for the HuggingChat handoff. Open the saved
prompt from Files, inspect it and paste it into the website manually. The brief
includes only selected project text, niche and audience. Do not paste credentials
or confidential information into a public comparison service.

Ask for the specified JSON response, save it as `/mnt/xxix-share/cleaning-draft.json`
and import it into a **new** project:

```sh
python3 video-pilot/elmatrix_video.py import-draft \
  --provider arena \
  --input /mnt/xxix-share/cleaning-draft.json \
  --output "$HOME/elmatrix-videos/cleaning-ai-001"
```

The importer accepts only schema/title/description/script, bounds lengths and checks
70–120 words and compatibility with the current English cloud narrator. Extra
instructions or executable fields are rejected, and nothing is executed. A single
JSON code fence is accepted; surrounding prose is not. Structural validation is
not fact-checking or a guarantee of copyright, safety or audience suitability.
The provider label is user supplied, not cryptographic proof of origin.

Review `cleaning-ai-001/project.json` before passing that new project to prepare-cloud.
The original project is preserved. This workflow spends no API credits and does not
activate paid fallbacks, render automatically or publish. It does not guarantee that
a provider's website is free or available. Future API access needs separately verified
account rights, cost controls and a live test; no such access is claimed here.

Sources:
- https://huggingface.co/docs/inference-providers/pricing
- https://platform.arena.ai/docs/claude-code
- https://platform.arena.ai/docs/opencode
