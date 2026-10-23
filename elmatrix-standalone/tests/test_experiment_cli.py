"""Regression tests for safe Elmatrix experiment CLI writes."""
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from elmatrix.cli import main
from elmatrix.evidence import open_db


class ExperimentCliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.home = Path(self.tempdir.name) / "elmatrix-home"
        self.env = patch.dict(os.environ, {"ELMATRIX_HOME": str(self.home)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.tempdir.cleanup)

    def invoke(self, argv):
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def experiment_count(self):
        with open_db() as db:
            return db.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]

    def test_unknown_opportunity_is_rejected_without_database_write(self):
        code, _, err = self.invoke([
            "experiment", "--opportunity", "not-a-real-id",
            "--hypothesis", "Test", "--metric", "signups", "--target", "10",
        ])
        self.assertEqual(code, 2)
        self.assertIn("unknown opportunity", err)
        self.assertEqual(self.experiment_count(), 0)

    def test_empty_required_text_is_rejected(self):
        code, _, err = self.invoke([
            "experiment", "--opportunity", "content-short-tutorials",
            "--hypothesis", "   ", "--metric", "signups", "--target", "10",
        ])
        self.assertEqual(code, 2)
        self.assertIn("must not be empty", err)
        self.assertEqual(self.experiment_count(), 0)

    def test_oversized_text_is_rejected(self):
        code, _, err = self.invoke([
            "experiment", "--opportunity", "content-short-tutorials",
            "--hypothesis", "x" * 2001, "--metric", "signups", "--target", "10",
        ])
        self.assertEqual(code, 2)
        self.assertIn("exceeds 2000 characters", err)
        self.assertEqual(self.experiment_count(), 0)

    def test_valid_experiment_is_trimmed_and_saved(self):
        code, out, _ = self.invoke([
            "experiment", "--opportunity", "content-short-tutorials",
            "--hypothesis", "  Test demand  ", "--metric", "  signups  ", "--target", "  10 users  ",
        ])
        self.assertEqual(code, 0)
        self.assertIn("Experiment recorded", out)
        with open_db() as db:
            row = db.execute(
                "SELECT opportunity_id, hypothesis, metric, target FROM experiments"
            ).fetchone()
            self.assertEqual(tuple(row), (
                "content-short-tutorials", "Test demand", "signups", "10 users"
            ))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM experiments").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
