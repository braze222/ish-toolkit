import json
import tempfile
import unittest
from pathlib import Path

from elmatrix.cli import main


class ExportSafetyTests(unittest.TestCase):
    def test_json_export_creates_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "catalog.json"
            result = main(["export", "--format", "json", "--output", str(dest)])
            self.assertEqual(result, 0)
            self.assertGreaterEqual(len(json.loads(dest.read_text())), 1)

    def test_export_refuses_to_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "existing.json"
            dest.write_text("KEEP THIS CONTENT")
            with self.assertRaises(SystemExit) as caught:
                main(["export", "--format", "json", "--output", str(dest)])
            self.assertEqual(caught.exception.code, 2)
            self.assertEqual(dest.read_text(), "KEEP THIS CONTENT")

    def test_export_refuses_symlink_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target.txt"
            link = Path(tmp) / "export.csv"
            target.write_text("PROTECT THIS TARGET")
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation is unavailable on this platform")

            with self.assertRaises(SystemExit) as caught:
                main(["export", "--format", "csv", "--output", str(link)])
            self.assertEqual(caught.exception.code, 2)
            self.assertEqual(target.read_text(), "PROTECT THIS TARGET")
            self.assertTrue(link.is_symlink())

    def test_csv_export_creates_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "catalog.csv"
            result = main(["export", "--format", "csv", "--output", str(dest)])
            self.assertEqual(result, 0)
            self.assertTrue(dest.read_text().strip())


if __name__ == "__main__":
    unittest.main()
