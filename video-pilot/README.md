# Elmatrix video pilot

A separate, explicit workflow: original script starter → your cover and narration →
portrait MP4 → private YouTube upload. Existing `elmatrix scan`, vault and toolkit
installation are untouched. This is a manually operated pilot, not an autonomous
AI generator, scheduler, monetization system or production release.

## Requirements and installation

Python 3.10+, FFmpeg/ffprobe with libx264 and AAC, and (for upload only) the Python
packages in requirements.txt. Render on a computer first. iSH performance and OAuth
browser handoff have not been validated. Do not treat Linux tests as iPhone support.

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
