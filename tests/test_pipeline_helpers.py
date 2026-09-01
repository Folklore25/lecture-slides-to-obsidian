import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills/lecture-slides-to-obsidian"
CANVAS_SKILL = REPO / "skills/obsidian-canvas-designer"
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
            aesthetic_check = staging / "canvas-aesthetic-check.json"
            render_metrics = staging / "canvas-render-metrics.json"
            render_check = staging / "canvas-render-check.json"
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
                    sys.executable, str(CANVAS_SKILL / "scripts/build-canvas.py"),
                    "--note", str(note), "--vault-root", str(vault),
                    "--profile", "policy-document", "--model", str(recall_model),
                    "--output", str(canvas),
                ],
                [
                    sys.executable, str(SKILL / "scripts/fill-report.py"),
                    "--context", str(REPORT_CONTEXT), "--output", str(report),
                ],
            ]
            for command in commands:
                result = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            aesthetic = subprocess.run(
                [
                    sys.executable, str(CANVAS_SKILL / "scripts/canvas-aesthetic-qa.py"),
                    "--canvas", str(canvas), "--output", str(aesthetic_check),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(aesthetic.returncode, 0, aesthetic.stdout + aesthetic.stderr)
            render_metrics.write_text(json.dumps({
                "schema_version": 1,
                "mode": "measure",
                "measurement_complete": True,
                "nodes": [{"id": "synthetic", "required_height": 300}],
            }))
            render_check.write_text(json.dumps({
                "schema_version": 1,
                "mode": "check",
                "measurement_complete": True,
                "valid": True,
                "canvas_sha256": hashlib.sha256(canvas.read_bytes()).hexdigest(),
            }))
            validation = subprocess.run(
                [
                    sys.executable, str(SKILL / "scripts/validate-output.py"),
                    str(folder), "--vault-root", str(vault), "--report", str(report),
                    "--recall-model", str(recall_model),
                    "--aesthetic-check", str(aesthetic_check),
                    "--render-metrics", str(render_metrics),
                    "--render-check", str(render_check),
                    "--delete-qa-on-success",
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
            self.assertTrue(note.is_file())
            self.assertTrue(canvas.is_file())
            self.assertTrue((folder / "assets").is_dir())
            self.assertFalse((folder / "conversion-report.md").exists())
            self.assertFalse(report.exists())
            self.assertFalse(recall_model.exists())
            self.assertFalse(aesthetic_check.exists())
            self.assertFalse(render_metrics.exists())
            self.assertFalse(render_check.exists())


if __name__ == "__main__":
    unittest.main()
