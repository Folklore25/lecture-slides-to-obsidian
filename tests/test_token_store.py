import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/token-store.py"
SPEC = importlib.util.spec_from_file_location("token_store", SCRIPT)
TOKEN_STORE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(TOKEN_STORE)
TOKEN_STORE.ITERATIONS = 10_000


class TokenStoreTests(unittest.TestCase):
    def test_round_trip_is_encrypted_and_private(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "mineru-api-token.enc.json"
            token = "synthetic-mineru-token-for-tests"
            passphrase = "correct horse battery staple"
            TOKEN_STORE.store_token(token, passphrase, path)
            self.assertNotIn(token, path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(TOKEN_STORE.load_token(passphrase, path), token)

    def test_wrong_passphrase_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "mineru-api-token.enc.json"
            TOKEN_STORE.store_token(
                "synthetic-mineru-token-for-tests",
                "correct horse battery staple",
                path,
            )
            with self.assertRaises(TOKEN_STORE.TokenStoreError):
                TOKEN_STORE.load_token("wrong passphrase value", path)

    def test_tampering_is_rejected_before_decryption(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "mineru-api-token.enc.json"
            passphrase = "correct horse battery staple"
            TOKEN_STORE.store_token("synthetic-mineru-token-for-tests", passphrase, path)
            payload = json.loads(path.read_text())
            payload["ciphertext"] = payload["ciphertext"][:-2] + "AA"
            path.write_text(json.dumps(payload))
            with self.assertRaises(TOKEN_STORE.TokenStoreError):
                TOKEN_STORE.load_token(passphrase, path)

    def test_delete_removes_only_token_file(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            path = folder / "mineru-api-token.enc.json"
            unrelated = folder / "course-registry.yaml"
            unrelated.write_text("schema_version: 2\n")
            TOKEN_STORE.store_token(
                "synthetic-mineru-token-for-tests",
                "correct horse battery staple",
                path,
            )
            self.assertTrue(TOKEN_STORE.delete_token(path))
            self.assertFalse(path.exists())
            self.assertTrue(unrelated.exists())


if __name__ == "__main__":
    unittest.main()
