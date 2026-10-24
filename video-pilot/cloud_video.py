"""Data-only handoff for iSH; rendering happens in an interactive cloud notebook."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import zipfile

class CloudError(ValueError):
    pass


MAX_RESULT = 128 * 1024 * 1024


def is_ish():
    return hasattr(os, 'uname') and 'ish' in os.uname().release.lower()


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')


def validated(data):
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise CloudError('Unsupported project schema')
    result = {'schema': 1}
    for key, limit in [('title', 100), ('description', 4500), ('script', 2000)]:
        value = data.get(key)
        if (not isinstance(value, str) or not value.strip() or len(value) > limit
                or any(ord(c) < 32 and c not in '\n\t' for c in value)
                or '<' in value or '>' in value):
            raise CloudError('Invalid ' + key)
        result[key] = value
    # This first synthetic voice/card implementation is English-only.
    if not result['script'].isascii() or not result['title'].isascii():
        raise CloudError('Cloud draft currently requires an English ASCII title and script')
    return result


def read_project(root):
    path = Path(root) / 'project.json'
    if path.stat().st_size > 65536:
        raise CloudError('Project too large')
    return validated(json.loads(path.read_text(encoding='utf-8')))


def fingerprint(data):
    return hashlib.sha256(canonical(validated(data))).hexdigest()


def exclusive_json(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(canonical(data)); out.flush(); os.fsync(out.fileno())


def prepare(root, destination):
    data = read_project(root)
    # Export only explicitly selected content. Never archive the project directory.
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_STORED) as archive:
        archive.writestr('project.json', canonical(data))
    print('Prepared script-only bundle:', destination)
    print('No credentials, vault files or local media included. Upload it to the notebook.')


def checked_members(archive, names, limit):
    entries = archive.infolist()
    if len(entries) != len(names) or {i.filename for i in entries} != set(names):
        raise CloudError('Unexpected, duplicate or missing archive entries')
    if sum(i.file_size for i in entries) > limit:
        raise CloudError('Archive exceeds size limit')
    for i in entries:
        mode = i.external_attr >> 16
        if (i.flag_bits & 1 or i.is_dir() or
                (mode & 0o170000) not in (0, 0o100000)):
            raise CloudError('Archive contains a nonregular or encrypted member')
        if i.filename.endswith('.json') and i.file_size > 65536:
            raise CloudError('Metadata too large')


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run_cloud(bundle, output):
    """Run on full Linux only, after notebook user explicitly starts the cell."""
    if is_ish():
        raise CloudError('Cloud renderer must run in the notebook, not iSH')
    for tool in ('ffmpeg', 'ffprobe', 'espeak-ng'):
        if not shutil.which(tool):
            raise CloudError('Cloud runtime missing ' + tool + '; run the setup cell')
    from PIL import Image, ImageDraw, ImageFont
    with zipfile.ZipFile(bundle) as archive:
        checked_members(archive, ['project.json'], 65536)
        data = validated(json.loads(archive.read('project.json')))
    with tempfile.TemporaryDirectory(prefix='elmatrix-cloud-') as directory:
        root = Path(directory)
        image = Image.new('RGB', (720, 1280), '#101b2d')
        draw = ImageDraw.Draw(image)
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        heading = ImageFont.truetype(font_path, 46)
        small = ImageFont.truetype(font_path, 26)
        draw.rounded_rectangle((46, 70, 674, 1210), radius=30, outline='#45d6bb', width=4)
        draw.text((82, 140), 'SERVICE CHECKLIST', font=small, fill='#45d6bb')
        y = 270
        for line in textwrap.wrap(data['title'], width=20):
            draw.text((82, y), line, font=heading, fill='white'); y += 66
        draw.text((82, 1080), 'Listen to the checklist', font=small, fill='#b8cadf')
        cover = root / 'cover.png'; image.save(cover)
        audio = root / 'narration.wav'
        subprocess.run(['espeak-ng', '-v', 'en', '-s', '155', '-w', str(audio), '--stdin'],
                       input=data['script'].encode(), check=True, timeout=120,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'json', str(audio)], check=True, capture_output=True, text=True, timeout=30)
        duration = float(json.loads(probe.stdout)['format']['duration'])
        if not 1 <= duration <= 180:
            raise CloudError('Narration exceeds pilot duration limit; shorten the script')
        video = root / 'video.mp4'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-loop', '1',
            '-i', str(cover), '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0',
            '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'stillimage',
            '-pix_fmt', 'yuv420p', '-r', '24', '-c:a', 'aac', '-b:a', '128k',
            '-t', str(duration), '-shortest', '-movflags', '+faststart', str(video)],
            check=True, timeout=1800, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
            'format=duration:stream=codec_type,width,height', '-of', 'json', str(video)],
            check=True, capture_output=True, text=True, timeout=30)
        info = json.loads(probe.stdout)
        if {s['codec_type'] for s in info['streams']} != {'video', 'audio'}:
            raise CloudError('Output is missing video/audio')
        if video.stat().st_size > MAX_RESULT - 65536:
            raise CloudError('Rendered file exceeds return-bundle limit')
        manifest = {'schema': 1, 'project_sha256': fingerprint(data),
            'sha256': file_hash(video), 'duration': duration, 'format': '720x1280 H.264/AAC',
            'voice': 'espeak-ng en; synthetic, not an imitation of a person',
            'renderer': 'cloud-draft-v1'}
        with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_STORED) as archive:
            archive.write(video, 'video.mp4')
            archive.writestr('render.json', canonical(manifest))
    return Path(output)


def import_result(root, bundle):
    root = Path(root).resolve(strict=True)
    data = read_project(root)
    for name in ('video.mp4', 'render.json', 'upload-attempt.json'):
        if os.path.lexists(root / name):
            raise CloudError('Project already has render/upload state; use a new project for revisions')
    with tempfile.TemporaryDirectory(prefix='.cloud-import-', dir=root) as directory:
        stage = Path(directory) / 'video.mp4'
        with zipfile.ZipFile(bundle) as archive:
            checked_members(archive, ['video.mp4', 'render.json'], MAX_RESULT)
            manifest = json.loads(archive.read('render.json'))
            if (not isinstance(manifest, dict) or manifest.get('schema') != 1 or
                    manifest.get('project_sha256') != fingerprint(data)):
                raise CloudError('Result does not match this project; nothing imported')
            h = hashlib.sha256(); total = 0
            with archive.open('video.mp4') as source, stage.open('xb') as out:
                while True:
                    block = source.read(1024 * 1024)
                    if not block: break
                    total += len(block)
                    if total > MAX_RESULT: raise CloudError('Video too large')
                    h.update(block); out.write(block)
                out.flush(); os.fsync(out.fileno())
            if h.hexdigest() != manifest.get('sha256'):
                raise CloudError('Result hash mismatch; nothing imported')
        with stage.open('rb') as stream:
            header = stream.read(12)
        if len(header) < 12 or header[4:8] != b'ftyp':
            raise CloudError('Not an MP4 container')
        os.chmod(stage, 0o600)
        os.link(stage, root / 'video.mp4')
        # A metadata-write failure leaves the video, blocks retry, and never enables upload.
        exclusive_json(root / 'render.json', manifest)
    print('Imported verified bundle into', root)
    print('Hash checks are not proof of trusted content. Watch the video before any upload.')


def doctor():
    if is_ish():
        return {'platform': 'ish', 'local_render': 'disabled',
                'reason': 'FFmpeg SIGSYS reported on iSH; no native binaries probed',
                'next': 'prepare-cloud, render in browser notebook, import-render',
                'cloud_execution': 'requires your interactive Google Colab session',
                'automatic_upload': False}
    return {'platform': 'other', 'local_render': 'not probed',
            'ffmpeg_on_path': bool(shutil.which('ffmpeg')),
            'ffprobe_on_path': bool(shutil.which('ffprobe')),
            'note': 'Presence does not prove execution compatibility'}
