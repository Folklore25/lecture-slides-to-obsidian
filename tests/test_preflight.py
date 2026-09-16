import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/preflight.py"
LEGACY_PROFILE = "paper"


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

    def base_arguments(self, source, vault, token, profile, extraction="native"):
        return [
            source, "--vault-root", vault, "--course", "COURSE101",
            "--profile", profile, "--extraction", extraction, "--language", "en",
            "--is-ocr", "false", "--token-file", token,
            "--loaded-skill", "obsidian-markdown",
            "--loaded-skill", "obsidian-cli",
            "--loaded-skill", "obsidian-canvas-designer",
        ]

    # --- content-driven lecture-notes synthesis -------------------------------

    def test_synthesis_preflight_passes_with_granularity_and_visual_input(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            code, result = run_preflight([
                *self.base_arguments(source, vault, token, "lecture-notes"),
                "--note-granularity", "single-note",
                "--visual-input", "true",
            ])
            self.assertEqual(code, 0, result["errors"] + [item["id"] for item in result["questions"]])
            self.assertEqual(result["checks"]["extraction"], "native")
            self.assertTrue(result["checks"]["content_driven_synthesis"])
            self.assertTrue(result["checks"]["native_visual_input"])
            self.assertEqual(result["checks"]["note_granularity"], "single-note")
            self.assertEqual(result["resolved"]["note_granularity"], "single-note")

    def test_lecture_notes_always_asks_the_user_for_note_granularity(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            _, result = run_preflight([
                *self.base_arguments(source, vault, token, "lecture-notes"),
                "--visual-input", "true",
            ])
            self.assertTrue(any(item["id"] == "note_granularity" for item in result["questions"]))

    def test_lecture_notes_requires_a_natively_multimodal_model(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            code, result = run_preflight([
                *self.base_arguments(source, vault, token, "lecture-notes"),
                "--note-granularity", "single-note",
                "--visual-input", "false",
            ])
            self.assertNotEqual(code, 0)
            self.assertTrue(any("natively multimodal" in item for item in result["errors"]))

    def test_lecture_notes_without_a_multimodal_answer_still_asks(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            _, result = run_preflight([
                *self.base_arguments(source, vault, token, "lecture-notes"),
                "--note-granularity", "single-note",
            ])
            self.assertTrue(any(item["id"] == "native_visual_input" for item in result["questions"]))

    def test_section_notes_granularity_is_rejected_for_other_profiles(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            code, result = run_preflight([
                *self.base_arguments(source, vault, token, LEGACY_PROFILE),
                "--note-granularity", "section-notes",
            ])
            self.assertNotEqual(code, 0)
            self.assertTrue(any("only supported for the lecture-notes" in item for item in result["errors"]))

    def test_native_extraction_needs_no_mineru_cli_or_token(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            code, result = run_preflight([
                *self.base_arguments(source, vault, token, LEGACY_PROFILE, "native"),
                "--visual-input", "true",
            ])
            self.assertEqual(code, 0, result["errors"])
            self.assertEqual(result["checks"]["extraction"], "native")
            self.assertEqual(result["checks"]["mineru_token"], "not-required")
            self.assertEqual(result["checks"]["language"], "not-applicable")
            self.assertTrue(result["checks"]["native_visual_input"])

    # --- profile selection ----------------------------------------------------

    def test_policy_filename_suggests_profile_before_upload(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp), "example-policy.pdf")
            _, result = run_preflight([
                source, "--vault-root", vault, "--course", "COURSE101",
                "--language", "en", "--is-ocr", "false", "--token-file", token,
                "--loaded-skill", "obsidian-markdown",
                "--loaded-skill", "obsidian-canvas-designer",
                "--loaded-skill", "obsidian-cli",
            ])
            profile_question = next(item for item in result["questions"] if item["id"] == "profile")
            self.assertIn("policy-document", profile_question["prompt"])

    def test_explicit_profile_conflict_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp), "example-policy.pdf")
            _, result = run_preflight([
                *self.base_arguments(source, vault, token, "lecture-notes"),
            ])
            self.assertTrue(any(item["id"] == "profile_mismatch" for item in result["questions"]))

    def test_missing_helper_skill_is_error(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            _, result = run_preflight([
                source, "--vault-root", vault, "--course", "COURSE101",
                "--profile", LEGACY_PROFILE, "--language", "en",
                "--is-ocr", "false", "--token-file", token,
                "--loaded-skill", "obsidian-markdown",
                "--loaded-skill", "obsidian-cli",
            ])
            self.assertTrue(any("obsidian-canvas-designer" in item for item in result["errors"]))

    def test_language_auto_requires_concrete_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            _, result = run_preflight([
                source, "--vault-root", vault, "--course", "COURSE101",
                "--profile", LEGACY_PROFILE, "--extraction", "mineru", "--language", "auto",
                "--is-ocr", "false", "--token-file", token,
                "--loaded-skill", "obsidian-markdown",
                "--loaded-skill", "obsidian-canvas-designer",
                "--loaded-skill", "obsidian-cli",
            ])
            self.assertTrue(any(item["id"] == "language" for item in result["questions"]))

    def test_mineru_mode_needs_no_visual_input_decision(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            code, result = run_preflight(
                self.base_arguments(source, vault, token, LEGACY_PROFILE, "mineru")
            )
            self.assertEqual(code, 0, result["errors"])
            self.assertNotIn("native_visual_input", result["checks"])
            self.assertEqual(result["checks"]["extraction"], "mineru")
            self.assertIn("encrypted_token_file", result["checks"])

    # --- deterministic LaTeX refinement ---------------------------------------

    def test_optional_latex_refinement_requires_loaded_skill(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            _, result = run_preflight([
                *self.base_arguments(source, vault, token, LEGACY_PROFILE, "mineru"),
                "--latex-refinement",
            ])
            self.assertTrue(any("obsidian-latex-refiner" in item for item in result["errors"]))

    def test_optional_latex_refinement_accepts_loaded_skill(self):
        with tempfile.TemporaryDirectory() as temp:
            source, vault, token = self.make_paths(Path(temp))
            code, result = run_preflight([
                *self.base_arguments(source, vault, token, LEGACY_PROFILE, "mineru"),
                "--loaded-skill", "obsidian-latex-refiner",
                "--latex-refinement",
            ])
            self.assertEqual(code, 0, result["errors"])
            self.assertTrue(result["checks"]["latex_refinement"])


if __name__ == "__main__":
    unittest.main()
