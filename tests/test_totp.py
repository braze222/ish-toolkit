import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pyotp

import tools.totp as totp
import tools.vault as vault


class TOTPTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

        self.vdir = Path(self.tmp.name) / ".vault"
        self.vdb = self.vdir / "vault-v2.db"
        self.salt = self.vdir / "salt"
        self.ver = self.vdir / "verify"

        self.patches = [
            patch.object(vault, "VDIR", self.vdir),
            patch.object(totp, "VDIR", self.vdir),
        ]

        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()

        self.tmp.cleanup()

    def init_vault(self):
        password = "TOTP-Test-Master-123!"

        with patch.object(
            vault.getpass,
            "getpass",
            side_effect=[password, password],
        ):
            vault.init()

        return password

    def add_totp(self, password, name="test-account"):
        secret = "JBSWY3DPEHPK3PXP"

        with patch.object(
            totp.getpass,
            "getpass",
            return_value=password,
        ):
            totp.add(name, secret)

        return secret

    def test_add_and_list_totp(self):
        password = self.init_vault()

        self.add_totp(password)

        output = io.StringIO()

        with redirect_stdout(output):
            totp.ls()

        self.assertEqual(
            output.getvalue().strip(),
            "test-account",
        )

    def test_totp_secret_is_encrypted(self):
        password = self.init_vault()
        secret = self.add_totp(password)

        conn = sqlite3.connect(self.vdb)

        try:
            row = conn.execute(
                "SELECT blob FROM totp WHERE name=?",
                ("test-account",),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row)
        self.assertNotIn(secret.encode(), row[0])

    def test_totp_generates_valid_code(self):
        password = self.init_vault()
        secret = self.add_totp(password)

        output = io.StringIO()

        with patch.object(
            totp.getpass,
            "getpass",
            return_value=password,
        ):
            with redirect_stdout(output):
                totp.show("test-account")

        expected = pyotp.TOTP(secret).now()

        self.assertIn(
            expected,
            output.getvalue(),
        )

    def test_delete_totp(self):
        password = self.init_vault()

        self.add_totp(password)

        with patch.object(
            totp.getpass,
            "getpass",
            return_value=password,
        ):
            totp.rm("test-account")

        conn = sqlite3.connect(self.vdb)

        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM totp WHERE name=?",
                ("test-account",),
            ).fetchone()[0]
        finally:
            conn.close()

        self.assertEqual(count, 0)

    def test_invalid_totp_secret_rejected(self):
        password = self.init_vault()

        with patch.object(
            totp.getpass,
            "getpass",
            return_value=password,
        ):
            with self.assertRaises(SystemExit) as result:
                totp.add(
                    "bad-account",
                    "NOT-A-VALID-TOTP-SECRET",
                )

        self.assertEqual(result.exception.code, 1)

        conn = sqlite3.connect(self.vdb)

        try:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='totp'"
            ).fetchone()
            count = conn.execute("SELECT COUNT(*) FROM totp").fetchone()[0] if exists else 0
        finally:
            conn.close()

        self.assertEqual(count, 0)

    def test_wrong_password_rejected(self):
        password = self.init_vault()

        self.add_totp(password)

        with patch.object(
            totp.getpass,
            "getpass",
            return_value="Wrong-Password-123!",
        ):
            with self.assertRaises(SystemExit) as result:
                totp.show("test-account")

        self.assertEqual(result.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
