"""Real cloud renderer exercise; needs espeak-ng, Pillow, FFmpeg and fonts."""
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cloud_video as cloud
import elmatrix_video as video

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory); root = base / 'project'
    video.init(root)
    path = root / 'project.json'
    data = json.loads(path.read_text()); data['script'] = 'Compare the scope before booking a cleaner.'
    path.write_text(json.dumps(data))
    cloud.prepare(root, base / 'job.zip')
    cloud.run_cloud(base / 'job.zip', base / 'result.zip')
    cloud.import_result(root, base / 'result.zip')
    info = video.probe(root / 'video.mp4')
    stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
    assert (stream['width'], stream['height']) == (720, 1280)
    assert any(s['codec_type'] == 'audio' for s in info['streams'])
    assert float(info['format']['duration']) > 1
print('PASS: original card, real synthetic narration, real MP4, bundle import')
