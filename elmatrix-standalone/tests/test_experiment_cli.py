"""Regression tests for safe Elmatrix experiment CLI writes and outcomes."""
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
        env_patch = patch.dict(os.environ, {"ELMATRIX_HOME": str(self.home)})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        self.addCleanup(self.tempdir.cleanup)

    def invoke(self, argv):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def rows(self):
        with open_db() as db:
            return [tuple(row) for row in db.execute(
                "SELECT id, opportunity_id, hypothesis, metric, target, result FROM experiments ORDER BY id"
            )]

    def test_unknown_opportunity_rejected_without_write(self):
        code, _, err = self.invoke(["experiment", "--opportunity", "not-real",
            "--hypothesis", "Test", "--metric", "signups", "--target", "10"])
        self.assertEqual(code, 2)
        self.assertIn("unknown opportunity", err)
        self.assertEqual(self.rows(), [])

    def test_blank_required_text_rejected(self):
        code, _, err = self.invoke(["experiment", "--opportunity", "content-short-tutorials",
            "--hypothesis", "   ", "--metric", "signups", "--target", "10"])
        self.assertEqual(code, 2)
        self.assertIn("must not be empty", err)
        self.assertEqual(self.rows(), [])

    def test_oversized_text_rejected(self):
        code, _, err = self.invoke(["experiment", "--opportunity", "content-short-tutorials",
            "--hypothesis", "x" * 2001, "--metric", "signups", "--target", "10"])
        self.assertEqual(code, 2)
        self.assertIn("exceeds 2000 characters", err)
        self.assertEqual(self.rows(), [])

    def test_valid_experiment_is_trimmed_and_gets_id(self):
        code, out, _ = self.invoke(["experiment", "--opportunity", "content-short-tutorials",
            "--hypothesis", " Test demand ", "--metric", " signups ", "--target", " 10 users "])
        self.assertEqual(code, 0)
        self.assertIn("Experiment #1 recorded", out)
        self.assertEqual(self.rows(), [(1, "content-short-tutorials", "Test demand", "signups", "10 users", "")])

    def test_outcome_rejects_unknown_id_and_empty_or_oversized_result(self):
        for result in ("   ", "x" * 2001):
            code, _, _ = self.invoke(["experiment-result", "--id", "1", "--result", result])
            self.assertEqual(code, 2)
        code, _, err = self.invoke(["experiment-result", "--id", "99", "--result", "10 signups"])
        self.assertEqual(code, 2)
        self.assertIn("unknown experiment ID", err)
        self.assertEqual(self.rows(), [])

    def test_outcome_updates_only_target_experiment(self):
        for hypothesis in ("First", "Second"):
            code, _, _ = self.invoke(["experiment", "--opportunity", "content-short-tutorials",
                "--hypothesis", hypothesis, "--metric", "signups", "--target", "10"])
            self.assertEqual(code, 0)
        code, out, _ = self.invoke(["experiment-result", "--id", "1", "--result", "  7 signups in 3 days  "])
        self.assertEqual(code, 0)
        self.assertIn("not an automatic validation verdict", out)
        rows = self.rows()
        self.assertEqual(rows[0][-1], "7 signups in 3 days")
        self.assertEqual(rows[1][-1], "")


if __name__ == "__main__":
    unittest.main()
