import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import tools.vault as vault


class VaultTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vdir = Path(self.tmp.name) / ".vault"
        self.vdb = self.vdir / "vault-v2.db"
        self.salt = self.vdir / "salt"
        self.ver = self.vdir / "verify"

        self.patches = [
            patch.object(vault, "VDIR", self.vdir),
        ]

        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def init_vault(self, password="Test-Master-Password-123!"):
        with patch.object(
            vault.getpass,
            "getpass",
            side_effect=[password, password],
        ):
            vault.init()

        return password

    def set_secret(self, password, name, value):
        with patch.object(
            vault.getpass,
            "getpass",
            side_effect=[password, value],
        ):
            vault.set_s(name)

    def test_initialize_creates_secure_vault(self):
        self.init_vault()

        self.assertTrue(self.vdir.exists())
        self.assertTrue(self.vdb.exists())
        self.assertFalse(self.salt.exists())
        self.assertFalse(self.ver.exists())

        self.assertEqual(self.vdir.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.vdb.stat().st_mode & 0o777, 0o600)

    def test_secret_round_trip(self):
        password = self.init_vault()

        self.set_secret(password, "test", "hello-secure-world")

        output = io.StringIO()
        with patch.object(vault.getpass, "getpass", return_value=password):
            with redirect_stdout(output):
                vault.get_s("test")

        self.assertEqual(output.getvalue().strip(), "hello-secure-world")

    def test_wrong_password_fails(self):
        password = self.init_vault()

        self.set_secret(password, "test", "secret")

        with patch.object(
            vault.getpass,
            "getpass",
            return_value="Definitely-Wrong-Password!",
        ):
            with self.assertRaises(SystemExit):
                vault.get_s("test")

    def test_delete_secret(self):
        password = self.init_vault()

        self.set_secret(password, "test", "temporary")

        with patch.object(vault.getpass, "getpass", return_value=password):
            vault.rm("test")

        conn = sqlite3.connect(self.vdb)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM secrets WHERE key=?",
                ("test",),
            ).fetchone()[0]
        finally:
            conn.close()

        self.assertEqual(count, 0)

    def test_empty_vault(self):
        self.init_vault()

        conn = sqlite3.connect(self.vdb)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM secrets"
            ).fetchone()[0]
        finally:
            conn.close()

        self.assertEqual(count, 0)

    def test_list_contains_secret(self):
        password = self.init_vault()

        self.set_secret(password, "alpha", "one")
        self.set_secret(password, "beta", "two")

        output = io.StringIO()
        with redirect_stdout(output):
            vault.ls()

        lines = output.getvalue().splitlines()

        self.assertEqual(lines, ["alpha", "beta"])

    def test_missing_secret_fails(self):
        password = self.init_vault()

        with patch.object(vault.getpass, "getpass", return_value=password):
            with self.assertRaises(SystemExit):
                vault.get_s("does-notnot-exist")

    def test_rotation_preserves_secrets_and_totp(self):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import os
        old = self.init_vault()
        self.set_secret(old, 'sample', 'retained-value')
        with sqlite3.connect(self.vdb) as conn:
            salt = conn.execute("SELECT salt FROM vault_meta").fetchone()[0]
        old_key = vault.derive(old, salt)
        nonce = os.urandom(12)
        blob = nonce + AESGCM(old_key).encrypt(nonce, b'JBSWY3DPEHPK3PXP', b'account')
        with sqlite3.connect(self.vdb) as conn:
            conn.execute('INSERT INTO totp VALUES (?, ?)', ('account', blob))
        new = 'Different-Master-Password-456!'
        with patch.object(vault.getpass, 'getpass', side_effect=[old, new, new]):
            vault.passwd()
        with sqlite3.connect(self.vdb) as conn:
            salt = conn.execute("SELECT salt FROM vault_meta").fetchone()[0]
        key = vault.derive(new, salt)
        with sqlite3.connect(self.vdb) as conn:
            blob = conn.execute('SELECT blob FROM totp').fetchone()[0]
        self.assertEqual(AESGCM(key).decrypt(blob[:12], blob[12:], b'account'), b'JBSWY3DPEHPK3PXP')
        output = io.StringIO()
        with patch.object(vault.getpass, 'getpass', return_value=new), redirect_stdout(output):
            vault.get_s('sample')
        self.assertEqual(output.getvalue().strip(), 'retained-value')


if __name__ == "__main__":
    unittest.main()
