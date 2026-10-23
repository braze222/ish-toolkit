"""Regression tests for installer rollback in an isolated temporary project."""
import os
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class InstallerRollbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ish-rollback-regression-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.bindir = Path(self.temp.name) / "bin"
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "tools").mkdir()
        (self.root / "lib").mkdir()
        self.bindir.mkdir()

        shutil.copy2(SOURCE_ROOT / "scripts" / "install.py",
                     self.root / "scripts" / "install.py")
        for dirname in ("tools", "lib"):
            shutil.copytree(SOURCE_ROOT / dirname, self.root / dirname,
                            dirs_exist_ok=True)

        (self.bindir / "ish").write_text("# original ish launcher\n")
        (self.bindir / "ish").chmod(0o755)
        (self.bindir / "ish-compute").symlink_to("original-target")

    def run_with_replace_failure(self, fail_on_call):
        real_replace = os.replace
        calls = 0

        def replacement(src, dst):
            nonlocal calls
            calls += 1
            if calls == fail_on_call:
                raise OSError("INTENTIONAL_TEST_FAILURE")
            return real_replace(src, dst)

        argv = [
            str(self.root / "scripts" / "install.py"),
            "--profile", "control",
            "--bin-dir", str(self.bindir),
        ]
        with patch.object(os, "replace", side_effect=replacement):
            with patch.object(sys, "argv", argv):
                with self.assertRaisesRegex(OSError, "INTENTIONAL_TEST_FAILURE"):
                    runpy.run_path(argv[0], run_name="__main__")

    def test_failed_replacement_restores_file_symlink_and_absence(self):
        # First replacement succeeds; second replacement fails.
        self.run_with_replace_failure(2)

        self.assertEqual(
            (self.bindir / "ish").read_text(),
            "# original ish launcher\n",
        )
        self.assertTrue((self.bindir / "ish").is_file())
        self.assertEqual(
            (self.bindir / "ish-compute").readlink(),
            Path("original-target"),
        )
        self.assertFalse((self.bindir / "ish-verify").exists())
        self.assertFalse((self.bindir / "ish-verify").is_symlink())

    def test_failure_removes_newly_created_launchers(self):
        self.run_with_replace_failure(4)
        self.assertEqual((self.bindir / "ish").read_text(), "# original ish launcher\n")
        self.assertEqual((self.bindir / "ish-compute").readlink(), Path("original-target"))
        for name in ("ish-compatibility", "ish-verify"):
            self.assertFalse((self.bindir / name).exists())
            self.assertFalse((self.bindir / name).is_symlink())

    def test_successful_install_replaces_expected_control_launchers(self):
        argv = [
            str(self.root / "scripts" / "install.py"),
            "--profile", "control",
            "--bin-dir", str(self.bindir),
        ]
        with patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as raised:
                runpy.run_path(argv[0], run_name="__main__")
        self.assertEqual(raised.exception.code, 0)

        for name in ("ish", "ish-compute", "ish-compatibility", "ish-verify"):
            target = self.bindir / name
            self.assertTrue(target.is_file(), f"missing launcher: {name}")
            self.assertTrue(os.access(target, os.X_OK), f"not executable: {name}")

        # Successful installation must preserve a recovery copy of prior launchers.
        backups = list(self.bindir.glob("ish-toolkit-install-backup-*"))
        self.assertTrue(backups, "expected a recovery backup directory")
        self.assertEqual(
            (backups[0] / "ish").read_text(),
            "# original ish launcher\n",
        )
        self.assertEqual(
            (backups[0] / "ish-compute").readlink(),
            Path("original-target"),
        )


    def test_failed_install_keeps_recovery_backup(self):
        self.run_with_replace_failure(2)

        backups = list(self.bindir.glob("ish-toolkit-install-backup-*"))
        self.assertEqual(len(backups), 1, "expected one retained recovery backup")
        self.assertEqual(
            (backups[0] / "ish").read_text(),
            "# original ish launcher\n",
        )
        self.assertEqual(
            (backups[0] / "ish-compute").readlink(),
            Path("original-target"),
        )

    def test_backup_creation_failure_does_not_replace_launchers(self):
        original_copy2 = shutil.copy2

        def fail_backup(src, dst, *args, **kwargs):
            if Path(src).name == "ish":
                raise OSError("SIMULATED_BACKUP_FAILURE")
            return original_copy2(src, dst, *args, **kwargs)

        argv = [
            str(self.root / "scripts" / "install.py"),
            "--profile", "control",
            "--bin-dir", str(self.bindir),
        ]
        with patch("shutil.copy2", side_effect=fail_backup):
            with patch.object(sys, "argv", argv):
                with self.assertRaisesRegex(OSError, "SIMULATED_BACKUP_FAILURE"):
                    runpy.run_path(argv[0], run_name="__main__")

        self.assertEqual(
            (self.bindir / "ish").read_text(),
            "# original ish launcher\n",
        )
        self.assertEqual(
            (self.bindir / "ish-compute").readlink(),
            Path("original-target"),
        )
        self.assertFalse((self.bindir / "ish-verify").exists())

    def test_rollback_failure_reports_recovery_location(self):
        real_replace = os.replace
        real_copy2 = shutil.copy2
        replace_calls = 0
        ish_copy_calls = 0

        def fail_second_replace(src, dst):
            nonlocal replace_calls
            replace_calls += 1
            if replace_calls == 2:
                raise OSError("SIMULATED_REPLACEMENT_FAILURE")
            return real_replace(src, dst)

        def fail_restore(src, dst, *args, **kwargs):
            nonlocal ish_copy_calls
            if Path(src).name == "ish":
                ish_copy_calls += 1
                # First copy backs up the original; second attempts restoration.
                if ish_copy_calls >= 2:
                    raise OSError("SIMULATED_RESTORE_FAILURE")
            return real_copy2(src, dst, *args, **kwargs)

        argv = [
            str(self.root / "scripts" / "install.py"),
            "--profile", "control",
            "--bin-dir", str(self.bindir),
        ]
        with patch.object(os, "replace", side_effect=fail_second_replace):
            with patch("shutil.copy2", side_effect=fail_restore):
                with patch.object(sys, "argv", argv):
                    with self.assertRaisesRegex(RuntimeError, "rollback also failed") as raised:
                        runpy.run_path(argv[0], run_name="__main__")

        self.assertIn("recovery backups retained at", str(raised.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
