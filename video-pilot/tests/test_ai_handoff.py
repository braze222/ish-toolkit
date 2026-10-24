import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_handoff as ai
import cloud_video as cloud
import elmatrix_video as video


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'; video.init(self.project)
        self.data = {'schema': 1, 'title': 'Compare cleaning quotes',
                     'description': 'A draft checklist.', 'script': 'Compare scope carefully. ' * 25}

    def test_prompt_only_exports_known_content(self):
        path = self.project / 'project.json'; data = json.loads(path.read_text())
        data['token'] = 'never-export'; path.write_text(json.dumps(data))
        out = self.root / 'prompt.txt'
        ai.prompt(self.project, 'arena', 'cleaning', 'adults in ZA', out)
        self.assertNotIn('never-export', out.read_text())
        self.assertIn('adults in ZA', out.read_text())
        with self.assertRaises(FileExistsError):
            ai.prompt(self.project, 'arena', 'cleaning', 'adults', out)

    def test_catalog_never_claims_free_api(self):
        self.assertFalse(ai.catalog()['paid_fallback'])
        for item in ai.catalog()['providers'].values():
            self.assertFalse(item['free_api_verified'])
            self.assertFalse(item['api_enabled'])

    def test_import_creates_new_unreviewed_project(self):
        source = self.root / 'draft.json'; source.write_text(json.dumps(self.data))
        target = self.root / 'new'
        ai.import_draft(source, target, 'huggingface')
        self.assertEqual(cloud.read_project(target), self.data)
        self.assertEqual(json.loads((target / 'draft-source.json').read_text())['review_status'], 'unreviewed')
        with self.assertRaises(FileExistsError): ai.import_draft(source, target, 'huggingface')

    def test_extra_fields_rejected(self):
        source = self.root / 'draft.json'
        source.write_text(json.dumps(dict(self.data, command='untrusted code')))
        with self.assertRaises(cloud.CloudError): ai.import_draft(source, self.root / 'new', 'arena')
        self.assertFalse((self.root / 'new').exists())

    def test_short_script_rejected(self):
        self.data['script'] = 'Too short.'
        source = self.root / 'draft.json'; source.write_text(json.dumps(self.data))
        with self.assertRaises(cloud.CloudError): ai.import_draft(source, self.root / 'new', 'arena')

    def test_json_fence_accepted_but_mixed_prose_rejected(self):
        source = self.root / 'draft.txt'
        source.write_text('```json\n' + json.dumps(self.data) + '\n```')
        ai.import_draft(source, self.root / 'new', 'arena')
        source.write_text('Explanation\n' + json.dumps(self.data))
        with self.assertRaises(ValueError): ai.import_draft(source, self.root / 'bad', 'arena')


if __name__ == '__main__': unittest.main()
