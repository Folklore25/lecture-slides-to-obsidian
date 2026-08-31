import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills/lecture-slides-to-obsidian"
CONTENT_LIST = REPO / "tests/fixtures/synthetic/content-list-v2-policy.json"
REPORT_CONTEXT = SKILL / "templates/report-context.example.json"
RECALL_MODEL = REPO / "tests/fixtures/synthetic/recall-model.policy.json"


class PipelineHelperTests(unittest.TestCase):
    def test_reconstruct_canvas_report_validate_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            vault = base / "vault"
            folder = vault / "COURSE101/Lectures/example-policy"
            staging = base / "staging"
            note = folder / "example-policy.md"
            canvas = folder / "example-policy.canvas"
            report = staging / "conversion-report.md"
            recall_model = staging / "recall-model.json"
            context = staging / "normalization.json"
            (folder / "assets").mkdir(parents=True)
            staging.mkdir()
            recall_model.write_text(RECALL_MODEL.read_text())

            commands = [
                [
                    sys.executable, str(SKILL / "scripts/reconstruct-note.py"),
                    "--page-groups", str(CONTENT_LIST),
                    "--profile", "policy-document", "--output", str(note),
                    "--context-output", str(context), "--title", "Example Policy",
                    "--course", "COURSE101", "--source-filename", "example-policy.pdf",
                    "--source-sha256", "0" * 64,
                ],
                [
                    sys.executable, str(SKILL / "scripts/build-canvas.py"),
                    "--note", str(note), "--vault-root", str(vault),
                    "--profile", "policy-document", "--model", str(recall_model),
                    "--output", str(canvas),
                ],
                [
                    sys.executable, str(SKILL / "scripts/fill-report.py"),
                    "--context", str(REPORT_CONTEXT), "--output", str(report),
                ],
                [
                    sys.executable, str(SKILL / "scripts/validate-output.py"),
                    str(folder), "--vault-root", str(vault), "--report", str(report),
                    "--recall-model", str(recall_model), "--delete-qa-on-success",
                ],
            ]
            for command in commands:
                result = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(note.is_file())
            self.assertTrue(canvas.is_file())
            self.assertTrue((folder / "assets").is_dir())
            self.assertFalse((folder / "conversion-report.md").exists())
            self.assertFalse(report.exists())
            self.assertFalse(recall_model.exists())


if __name__ == "__main__":
    unittest.main()
