"""Exercise the actual standalone verifier in disposable checkouts."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class VerifierTests(unittest.TestCase):
    def run_fixture(self, body=None):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'scripts').mkdir();(root/'elmatrix').mkdir();(root/'tests').mkdir()
            (root/'elmatrix'/'__init__.py').write_text('')
            verifier=root/'scripts'/'ish-verify'
            shutil.copy2(ROOT/'elmatrix-standalone'/'scripts'/'ish-verify',verifier)
            if body is not None:(root/'tests'/'test_example.py').write_text(body)
            return subprocess.run([sys.executable,str(verifier)],capture_output=True,text=True,timeout=20)
    def test_empty_suite_fails(self):
        result=self.run_fixture();self.assertEqual(result.returncode,1)
    def test_failed_assertion_fails(self):
        result=self.run_fixture('import unittest\nclass T(unittest.TestCase):\n def test_no(self): self.fail("expected")\n')
        self.assertEqual(result.returncode,1)
    def test_passing_test_passes(self):
        result=self.run_fixture('import unittest\nclass T(unittest.TestCase):\n def test_yes(self): self.assertEqual(2+2,4)\n')
        self.assertEqual(result.returncode,0)
