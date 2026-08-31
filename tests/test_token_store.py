import importlib.util
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/token-store.py"
SPEC = importlib.util.spec_from_file_location("token_store", SCRIPT)
TOKEN_STORE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(TOKEN_STORE)
TOKEN_STORE.ITERATIONS = 10_000
WRAPPING_SECRET = "synthetic-keychain-wrapping-secret-0123456789abcdef"


class TokenStoreTests(unittest.TestCase):
    def test_round_trip_is_encrypted_and_private(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "mineru-api-token.enc.json"
            token = "synthetic-mineru-token-for-tests"
            TOKEN_STORE.store_token(token, WRAPPING_SECRET, path)
            self.assertNotIn(token, path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(TOKEN_STORE.load_token(WRAPPING_SECRET, path), token)

    def test_wrong_wrapping_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "mineru-api-token.enc.json"
            TOKEN_STORE.store_token(
                "synthetic-mineru-token-for-tests",
                WRAPPING_SECRET,
                path,
            )
            with self.assertRaises(TOKEN_STORE.TokenStoreError):
                TOKEN_STORE.load_token("wrong-wrapping-secret-0123456789abcdef", path)

    def test_tampering_is_rejected_before_decryption(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "mineru-api-token.enc.json"
            TOKEN_STORE.store_token("synthetic-mineru-token-for-tests", WRAPPING_SECRET, path)
            payload = json.loads(path.read_text())
            payload["ciphertext"] = payload["ciphertext"][:-2] + "AA"
            path.write_text(json.dumps(payload))
            with self.assertRaises(TOKEN_STORE.TokenStoreError):
                TOKEN_STORE.load_token(WRAPPING_SECRET, path)

    def test_delete_removes_only_token_file(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            path = folder / "mineru-api-token.enc.json"
            unrelated = folder / "course-registry.yaml"
            unrelated.write_text("schema_version: 2\n")
            TOKEN_STORE.store_token(
                "synthetic-mineru-token-for-tests",
                WRAPPING_SECRET,
                path,
            )
            self.assertTrue(TOKEN_STORE.delete_token(path))
            self.assertFalse(path.exists())
            self.assertTrue(unrelated.exists())

    def test_auto_store_and_load_use_keychain_backend(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "mineru-api-token.enc.json"
            token = "synthetic-mineru-token-for-tests"
            with mock.patch.object(
                TOKEN_STORE, "get_or_create_wrapping_secret", return_value=WRAPPING_SECRET
            ), mock.patch.object(
                TOKEN_STORE, "get_wrapping_secret", return_value=WRAPPING_SECRET
            ):
                TOKEN_STORE.store_token_auto(token, path)
                self.assertEqual(TOKEN_STORE.load_token_auto(path), token)


if __name__ == "__main__":
    unittest.main()
