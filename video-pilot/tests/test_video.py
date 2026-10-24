import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import elmatrix_video as video

CHANNEL = 'UC' + 'a' * 22


class VideoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project'
        with contextlib.redirect_stdout(io.StringIO()):
            video.init(self.root)
        (self.root / 'video.mp4').write_bytes(b'test video fixture')
        video.write_new(self.root / 'render.json', {
            'sha256': video.digest(self.root / 'video.mp4')})
        self.api = MagicMock()
        self.api.channels.return_value.list.return_value.execute.return_value = {
            'items': [{'id': CHANNEL}]}
        self.api.videos.return_value.insert.return_value.next_chunk.return_value = (
            None, {'id': 'abcdefghijk'})
        module = types.ModuleType('googleapiclient.http')
        module.MediaFileUpload = MagicMock()
        self.patch = patch.dict(sys.modules, {'googleapiclient.http': module})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def upload(self, **kwargs):
        return video.upload(self.root, 'unused.json', CHANNEL, 'general', 'no',
                            service=self.api, **kwargs)

    def test_requires_review(self):
        with self.assertRaises(video.VideoError): self.upload(reviewed=False)
        self.api.videos.assert_not_called()

    def test_channel_mismatch_blocks_upload(self):
        self.api.channels.return_value.list.return_value.execute.return_value = {
            'items': [{'id': 'UC' + 'b' * 22}]}
        with self.assertRaises(video.VideoError): self.upload(reviewed=True)
        self.api.videos.assert_not_called()

    def test_changed_video_blocks_upload(self):
        (self.root / 'video.mp4').write_bytes(b'changed')
        with self.assertRaises(video.VideoError): self.upload(reviewed=True)
        self.api.channels.assert_not_called()

    def test_private_upload_receipt_and_duplicate_guard(self):
        with contextlib.redirect_stdout(io.StringIO()): self.upload(reviewed=True)
        call = self.api.videos.return_value.insert.call_args.kwargs
        self.assertEqual(call['body']['status']['privacyStatus'], 'private')
        self.assertFalse(call['notifySubscribers'])
        self.assertFalse(call['body']['status']['selfDeclaredMadeForKids'])
        receipt = video.read_json(self.root / 'upload-receipt.json')
        self.assertEqual(receipt['id'], 'abcdefghijk')
        with self.assertRaises(video.VideoError): self.upload(reviewed=True)
        self.assertEqual(self.api.videos.return_value.insert.call_count, 1)

    def test_network_failure_leaves_blocking_attempt(self):
        self.api.videos.return_value.insert.return_value.next_chunk.side_effect = OSError('offline')
        with self.assertRaises(OSError): self.upload(reviewed=True)
        self.assertTrue((self.root / 'upload-attempt.json').is_file())
        with self.assertRaises(video.VideoError): self.upload(reviewed=True)
        self.assertFalse((self.root / 'upload-receipt.json').exists())

    def test_exclusive_marker_rejects_symlink(self):
        target = Path(self.temp.name) / 'target'
        target.write_text('unchanged')
        (self.root / 'upload-attempt.json').symlink_to(target)
        with self.assertRaises(video.VideoError): self.upload(reviewed=True)
        self.assertEqual(target.read_text(), 'unchanged')

    def test_no_overwrite(self):
        with self.assertRaises(FileExistsError): video.init(self.root)
        with self.assertRaises(FileExistsError):
            video.write_new(self.root / 'project.json', {})

    def test_explicit_audience_and_synthetic_metadata(self):
        _, data = video.project(self.root)
        body = video.upload_body(data, 'kids', 'yes')
        self.assertTrue(body['status']['containsSyntheticMedia'])
        self.assertTrue(body['status']['selfDeclaredMadeForKids'])

    def test_invalid_title(self):
        path = self.root / 'project.json'
        data = video.read_json(path); data['title'] = '<invalid>'
        path.write_text(json.dumps(data))
        with self.assertRaises(video.VideoError): video.project(self.root)

    def test_oauth_error_does_not_print_secrets(self):
        stderr = io.StringIO()
        with patch.object(video, 'authorize', side_effect=RuntimeError('secret-token')):
            with contextlib.redirect_stderr(stderr):
                code = video.main(['upload', str(self.root), '--client-secrets', 'client.json',
                    '--channel', CHANNEL, '--audience', 'general', '--synthetic', 'no',
                    '--confirm-reviewed'])
        self.assertEqual(code, 1)
        self.assertNotIn('secret-token', stderr.getvalue())


if __name__ == '__main__': unittest.main()
