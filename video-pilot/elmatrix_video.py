#!/usr/bin/env python3
"""Explicit, local faceless-video pilot; private uploads only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
          'https://www.googleapis.com/auth/youtube.readonly']


class VideoError(Exception):
    pass


def read_json(path):
    if path.stat().st_size > 65536:
        raise VideoError('JSON file exceeds 64 KiB')
    return json.loads(path.read_text(encoding='utf-8'))


def write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as out:
        json.dump(data, out, ensure_ascii=False, indent=2)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def project(path):
    root = Path(path).resolve(strict=True)
    data = read_json(root / 'project.json')
    if data.get('schema') != 1:
        raise VideoError('Unsupported project schema')
    for name, limit in [('title', 100), ('description', 4500)]:
        value = data.get(name)
        if (not isinstance(value, str) or not value.strip() or len(value) > limit
                or '<' in value or '>' in value or '\x00' in value):
            raise VideoError('Invalid title or description')
    return root, data


def init(path):
    root = Path(path)
    root.mkdir(mode=0o700, parents=False, exist_ok=False)
    write_new(root / 'project.json', {
        'schema': 1,
        'title': 'Three questions to ask before booking a cleaner',
        'description': 'A short checklist for comparing cleaning-service quotes. '
                       'Ask each provider about scope, supplies, and access arrangements.',
        'script': 'Before booking a cleaner, ask three questions. First: which rooms '
                  'and tasks are included in the quote? Second: who supplies the '
                  'equipment and cleaning products? Third: how will access and '
                  'the final walkthrough work? Write down the answers so you can '
                  'compare quotes fairly. Save this checklist for your next booking.',
        'asset_notes': 'Record your own narration and create or license a portrait '
                       'cover image. Keep proof of rights. No assets are fetched.',
    })
    print(f'Created {root / "project.json"}; review and record the script.')


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe',
        '-show_entries', 'format=duration:stream=codec_type,width,height',
        '-of', 'json', str(path)], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise VideoError('ffprobe could not inspect media')
    return json.loads(result.stdout)


def render(path, image, audio):
    root, data = project(path)
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise VideoError('Install ffmpeg and ffprobe on the rendering computer')
    image, audio = Path(image).resolve(strict=True), Path(audio).resolve(strict=True)
    if image.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
        raise VideoError('Cover must be PNG or JPEG')
    if audio.suffix.lower() not in ('.wav', '.mp3', '.m4a'):
        raise VideoError('Narration must be WAV, MP3 or M4A')
    if not image.is_file() or not audio.is_file():
        raise VideoError('Media must be regular files')
    duration = float(probe(audio)['format']['duration'])
    if not 1 <= duration <= 180:
        raise VideoError('Narration must be between 1 and 180 seconds')
    destination = root / 'video.mp4'
    if destination.exists() or destination.is_symlink():
        raise VideoError('video.mp4 already exists; use a new project for revisions')
    with tempfile.TemporaryDirectory(prefix='.render-', dir=root) as temp:
        output = Path(temp) / 'video.mp4'
        command = ['ffmpeg', '-nostdin', '-v', 'error', '-n',
            '-protocol_whitelist', 'file,pipe', '-loop', '1', '-i', str(image),
            '-protocol_whitelist', 'file,pipe', '-i', str(audio),
            '-map', '0:v:0', '-map', '1:a:0', '-map_metadata', '-1',
            '-vf', 'scale=720:1280:force_original_aspect_ratio=decrease,'
                   'pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1',
            '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'stillimage',
            '-pix_fmt', 'yuv420p', '-r', '24', '-c:a', 'aac', '-b:a', '128k',
            '-t', str(duration), '-shortest', '-movflags', '+faststart', str(output)]
        result = subprocess.run(command, timeout=1800, capture_output=True)
        if result.returncode:
            raise VideoError('Rendering failed; check your media and ffmpeg installation')
        info = probe(output)
        kinds = {stream['codec_type'] for stream in info['streams']}
        if not {'video', 'audio'} <= kinds:
            raise VideoError('Rendered output lacks video or audio')
        os.chmod(output, 0o600)
        os.link(output, destination)  # exclusive publication, no overwrite
    write_new(root / 'render.json', {'sha256': digest(destination),
        'duration': duration, 'format': '720x1280 H.264/AAC',
        'image_sha256': digest(image), 'audio_sha256': digest(audio)})
    print(f'Rendered {destination}. Watch it and review the metadata before upload.')


def upload_body(data, audience, synthetic):
    return {'snippet': {'title': data['title'], 'description': data['description'],
                        'categoryId': '26'},
            'status': {'privacyStatus': 'private',
                       'selfDeclaredMadeForKids': audience == 'kids',
                       'containsSyntheticMedia': synthetic == 'yes'}}


def authorize(path):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    config = read_json(Path(path))
    settings = config.get('installed', {})
    if (settings.get('auth_uri') != 'https://accounts.google.com/o/oauth2/auth'
            or settings.get('token_uri') != 'https://oauth2.googleapis.com/token'):
        raise VideoError('Use a Google Desktop app OAuth client JSON with official endpoints')
    flow = InstalledAppFlow.from_client_config(config, SCOPES,
                                               autogenerate_code_verifier=True)
    credentials = flow.run_local_server(host='127.0.0.1', port=0,
        open_browser=False, timeout_seconds=300, access_type='online', prompt='consent')
    # Credentials remain in memory; no refresh token file is written.
    transport = AuthorizedHttp(credentials, http=httplib2.Http(timeout=60))
    return build('youtube', 'v3', http=transport, cache_discovery=False)


def upload(path, client_secrets, channel, audience, synthetic, reviewed, service=None):
    if not reviewed:
        raise VideoError('Watch the video, check rights and metadata, then use --confirm-reviewed')
    if not re.fullmatch(r'UC[A-Za-z0-9_-]{22}', channel):
        raise VideoError('Supply the exact UC... YouTube channel ID')
    root, data = project(path)
    video = root / 'video.mp4'
    render_info = read_json(root / 'render.json')
    checksum = digest(video)
    if checksum != render_info.get('sha256'):
        raise VideoError('Video differs from the recorded render')
    attempt = root / 'upload-attempt.json'
    if attempt.exists() or attempt.is_symlink():
        raise VideoError('Upload already attempted. Inspect receipt and YouTube Studio; do not retry blindly')
    service = service or authorize(client_secrets)
    channels = service.channels().list(part='id', mine=True).execute(num_retries=0)
    ids = [item['id'] for item in channels.get('items', [])]
    if ids != [channel]:
        raise VideoError('Authorized channel does not match the requested channel')
    from googleapiclient.http import MediaFileUpload
    body = upload_body(data, audience, synthetic)
    # Persist BEFORE any upload request. Uncertain outcomes block repeat attempts.
    write_new(attempt, {'state': 'started_or_unknown', 'channel': channel,
                       'sha256': checksum, 'metadata': body})
    request = service.videos().insert(part='snippet,status', body=body,
        notifySubscribers=False,
        media_body=MediaFileUpload(str(video), mimetype='video/mp4',
                                  chunksize=1024 * 1024, resumable=True))
    response = None
    while response is None:
        _, response = request.next_chunk(num_retries=0)
    video_id = response.get('id', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        raise VideoError('Upload response lacked a valid ID; check YouTube Studio')
    receipt = {'state': 'uploaded_processing_not_verified', 'id': video_id,
               'url': f'https://www.youtube.com/watch?v={video_id}',
               'channel': channel, 'requested_privacy': 'private', 'sha256': checksum}
    write_new(root / 'upload-receipt.json', receipt)
    print(json.dumps(receipt, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('init', help='create an original cleaning-service script starter')
    p.add_argument('project')
    p = commands.add_parser('render', help='render your cover image and recorded narration')
    p.add_argument('project'); p.add_argument('--image', required=True)
    p.add_argument('--audio', required=True)
    p = commands.add_parser('upload', help='authorize and upload privately; never auto-publish')
    p.add_argument('project'); p.add_argument('--client-secrets', required=True)
    p.add_argument('--channel', required=True)
    p.add_argument('--audience', choices=['general', 'kids'], required=True)
    p.add_argument('--synthetic', choices=['yes', 'no'], required=True)
    p.add_argument('--confirm-reviewed', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init': init(args.project)
        elif args.command == 'render': render(args.project, args.image, args.audio)
        else: upload(args.project, args.client_secrets, args.channel,
                     args.audience, args.synthetic, args.confirm_reviewed)
        return 0
    except VideoError as exc:
        print(f'Error: {exc}', file=sys.stderr)
    except ImportError:
        print('Install video-pilot/requirements.txt in a virtual environment.', file=sys.stderr)
    except KeyboardInterrupt:
        print('Interrupted. If uploading, check Studio before retrying.', file=sys.stderr)
    except Exception as exc:
        # Provider exception messages can contain credentials, request URLs or local paths.
        print(f'Operation failed ({type(exc).__name__}); no automatic retry. '
              'If uploading, check YouTube Studio and the project receipt.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
