"""Real cloud renderer exercise; needs espeak-ng, Pillow, FFmpeg and fonts."""
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import types
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
    # Reproduce a stale notebook module; the child must not inherit it.
    sys.modules['PIL._typing'] = types.ModuleType('PIL._typing')
    notebook = json.loads((Path(__file__).resolve().parents[1] / 'Colab_Render.ipynb').read_text())
    scope = {}
    exec(''.join(notebook['cells'][2]['source']), scope)
    renderer = base / 'renderer.py'
    renderer.write_text(scope['_ELMATRIX_RENDERER_SOURCE'])
    subprocess.run([sys.executable, '-I', '-c',
        "import runpy,sys; runpy.run_path(sys.argv[1])['run_cloud'](sys.argv[2],sys.argv[3])",
        str(renderer), str(base / 'job.zip'), str(base / 'result.zip')],
        check=True, timeout=2100)
    cloud.import_result(root, base / 'result.zip')
    info = video.probe(root / 'video.mp4')
    stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
    assert (stream['width'], stream['height']) == (720, 1280)
    assert any(s['codec_type'] == 'audio' for s in info['streams'])
    assert float(info['format']['duration']) > 1
print('PASS: original card, real synthetic narration, real MP4, bundle import')
