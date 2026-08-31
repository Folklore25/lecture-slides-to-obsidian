import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/fill-report.py"
CONTEXT_PATH = REPO / "skills/lecture-slides-to-obsidian/templates/report-context.example.json"
VALIDATOR = REPO / "skills/lecture-slides-to-obsidian/scripts/validate-output.py"
OUTPUT_FIXTURE = REPO / "tests/fixtures/synthetic/valid-document-folder"
SPEC = importlib.util.spec_from_file_location("fill_report", SCRIPT)
FILL_REPORT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(FILL_REPORT)


class FillReportTests(unittest.TestCase):
    def setUp(self):
        self.context = json.loads(CONTEXT_PATH.read_text())

    def test_context_renders_fixed_sections_and_numeric_inventory(self):
        report = FILL_REPORT.render_report(self.context)
        for section in (
            "Matched routing", "Pipeline", "Outputs", "Content inventory",
            "Quality gates", "Review items", "Not checked",
        ):
            self.assertIn(f"## {section}", report)
        self.assertIn("| Figures/images | 0 |", report)
        self.assertIn("Pixel-level visual diff", report)

    def test_review_items_are_machine_greppable(self):
        self.context["review_items"] = ["Confirm section hierarchy"]
        report = FILL_REPORT.render_report(self.context)
        self.assertIn("> [!warning] REVIEW", report)
        self.assertIn("> Confirm section hierarchy", report)

    def test_secret_field_is_rejected(self):
        self.context["pipeline"]["api_token"] = "synthetic-secret"
        with self.assertRaises(FILL_REPORT.ReportError):
            FILL_REPORT.render_report(self.context)

    def test_missing_inventory_field_is_rejected(self):
        del self.context["inventory"]["fallback_pages"]
        with self.assertRaises(FILL_REPORT.ReportError):
            FILL_REPORT.render_report(self.context)

    def test_rendered_report_validates_and_is_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            folder = base / "document"
            report = base / "staging/conversion-report.md"
            shutil.copytree(OUTPUT_FIXTURE, folder)
            FILL_REPORT.write_atomic(report, FILL_REPORT.render_report(self.context))
            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    str(folder),
                    "--fixture-mode",
                    "--report",
                    str(report),
                    "--delete-report-on-success",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
