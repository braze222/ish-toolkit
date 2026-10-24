import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cloud_video as cloud
import elmatrix_video as video


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.root = self.base / 'project'
        with contextlib.redirect_stdout(io.StringIO()): video.init(self.root)

    def result(self, changes=None, entries=None):
        payload = b'\x00\x00\x00\x18ftypisom' + b'test fixture'
        info = {'schema': 1, 'project_sha256': cloud.fingerprint(cloud.read_project(self.root)),
                'sha256': cloud.hashlib.sha256(payload).hexdigest()}
        info.update(changes or {})
        path = self.base / 'result.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('video.mp4', payload)
            archive.writestr('render.json', json.dumps(info))
            for name, data in (entries or []): archive.writestr(name, data)
        return path

    def test_ish_doctor_never_executes_native_program(self):
        with patch.object(cloud, 'is_ish', return_value=True), patch.object(cloud.subprocess, 'run') as run:
            self.assertEqual(cloud.doctor()['local_render'], 'disabled')
            run.assert_not_called()

    def test_ish_local_render_stops_before_probe(self):
        with patch.object(cloud, 'is_ish', return_value=True), patch.object(video, 'probe') as probe:
            with self.assertRaises(video.VideoError): video.render(self.root, 'missing', 'missing')
            probe.assert_not_called()

    def test_export_is_data_only_and_no_native_execution(self):
        path = self.root / 'project.json'
        data = json.loads(path.read_text()); data['api_key'] = 'must-not-export'
        path.write_text(json.dumps(data)); (self.root / 'token.json').write_text('secret')
        out = self.base / 'job.zip'
        with patch.object(cloud.subprocess, 'run') as run:
            cloud.prepare(self.root, out); run.assert_not_called()
        with zipfile.ZipFile(out) as archive:
            self.assertEqual(archive.namelist(), ['project.json'])
            self.assertNotIn(b'must-not-export', archive.read('project.json'))
        with self.assertRaises(FileExistsError): cloud.prepare(self.root, out)

    def test_import_no_native_execution_and_no_overwrite(self):
        bundle = self.result()
        with patch.object(cloud.subprocess, 'run') as run:
            cloud.import_result(self.root, bundle); run.assert_not_called()
        self.assertTrue((self.root / 'video.mp4').is_file())
        with self.assertRaises(cloud.CloudError): cloud.import_result(self.root, bundle)

    def test_mismatched_project_rejected(self):
        with self.assertRaises(cloud.CloudError):
            cloud.import_result(self.root, self.result({'project_sha256': 'wrong'}))
        self.assertFalse((self.root / 'video.mp4').exists())

    def test_hash_failure_rejected(self):
        with self.assertRaises(cloud.CloudError):
            cloud.import_result(self.root, self.result({'sha256': 'wrong'}))
        self.assertFalse((self.root / 'video.mp4').exists())

    def test_path_traversal_rejected(self):
        with self.assertRaises(cloud.CloudError):
            cloud.import_result(self.root, self.result(entries=[('../escape', 'bad')]))
        self.assertFalse((self.base / 'escape').exists())

    def test_archive_size_limit(self):
        bundle = self.result()
        with patch.object(cloud, 'MAX_RESULT', 10):
            with self.assertRaises(cloud.CloudError): cloud.import_result(self.root, bundle)

    def test_duplicate_archive_entry_rejected(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            bundle = self.result(entries=[('video.mp4', 'extra')])
        with self.assertRaises(cloud.CloudError): cloud.import_result(self.root, bundle)

    def test_link_destination_not_overwritten(self):
        target = self.base / 'keep'; target.write_text('keep')
        (self.root / 'video.mp4').symlink_to(target)
        with self.assertRaises(cloud.CloudError): cloud.import_result(self.root, self.result())
        self.assertEqual(target.read_text(), 'keep')

    def test_notebook_embeds_exact_reviewed_renderer(self):
        folder = Path(__file__).resolve().parents[1]
        notebook = json.loads((folder / 'Colab_Render.ipynb').read_text())
        scope = {}
        exec(''.join(notebook['cells'][2]['source']), scope)
        self.assertEqual(scope['_ELMATRIX_RENDERER_SOURCE'], (folder / 'cloud_video.py').read_text())
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code': compile(''.join(cell['source']), '<notebook>', 'exec')


if __name__ == '__main__': unittest.main()
