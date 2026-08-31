import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/preflight.py"


def run_preflight(arguments):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--fixture-mode", *map(str, arguments)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, json.loads(result.stdout)


class PreflightTests(unittest.TestCase):
    def make_paths(self, base: Path, filename="lecture.pdf"):
        source = base / "source" / filename
        vault = base / "vault"
        token = base / "state" / "mineru-api-token.enc.json"
        source.parent.mkdir()
        source.write_bytes(b"synthetic")
        vault.mkdir()
        token.parent.mkdir()
        token.write_text("{}")
        token.chmod(0o600)
        return source, vault, token

    def test_complete_preflight_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            code, result = run_preflight([
                source, "--vault-root", vault, "--course", "COURSE101",
                "--profile", "lecture-notes", "--language", "en",
                "--is-ocr", "false", "--token-file", token,
                "--loaded-skill", "obsidian-markdown",
                "--loaded-skill", "json-canvas",
                "--loaded-skill", "obsidian-cli",
            ])
            self.assertEqual(code, 0)
            self.assertTrue(result["ok"])

    def test_policy_filename_suggests_profile_before_upload(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp), "example-policy.pdf")
            _, result = run_preflight([
                source, "--vault-root", vault, "--course", "COURSE101",
                "--language", "en", "--is-ocr", "false", "--token-file", token,
                "--loaded-skill", "obsidian-markdown",
                "--loaded-skill", "json-canvas",
                "--loaded-skill", "obsidian-cli",
            ])
            profile_question = next(item for item in result["questions"] if item["id"] == "profile")
            self.assertIn("policy-document", profile_question["prompt"])

    def test_explicit_profile_conflict_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp), "example-policy.pdf")
            _, result = run_preflight([
                source, "--vault-root", vault, "--course", "COURSE101",
                "--profile", "lecture-notes", "--language", "en",
                "--is-ocr", "false", "--token-file", token,
                "--loaded-skill", "obsidian-markdown",
                "--loaded-skill", "json-canvas",
                "--loaded-skill", "obsidian-cli",
            ])
            self.assertTrue(any(item["id"] == "profile_mismatch" for item in result["questions"]))

    def test_missing_helper_skill_is_error(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            _, result = run_preflight([
                source, "--vault-root", vault, "--course", "COURSE101",
                "--profile", "lecture-notes", "--language", "en",
                "--is-ocr", "false", "--token-file", token,
                "--loaded-skill", "obsidian-markdown",
                "--loaded-skill", "obsidian-cli",
            ])
            self.assertTrue(any("json-canvas" in item for item in result["errors"]))

    def test_language_auto_requires_concrete_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            _, result = run_preflight([
                source, "--vault-root", vault, "--course", "COURSE101",
                "--profile", "lecture-notes", "--language", "auto",
                "--is-ocr", "false", "--token-file", token,
                "--loaded-skill", "obsidian-markdown",
                "--loaded-skill", "json-canvas",
                "--loaded-skill", "obsidian-cli",
            ])
            self.assertTrue(any(item["id"] == "language" for item in result["questions"]))


if __name__ == "__main__":
    unittest.main()
