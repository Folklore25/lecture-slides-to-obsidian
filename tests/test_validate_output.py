import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
VALIDATOR = REPO / "skills/lecture-slides-to-obsidian/scripts/validate-output.py"
FIXTURE = REPO / "tests/fixtures/synthetic/valid-document-folder"
REPORT_FIXTURE = REPO / "tests/fixtures/staging/conversion-report.md"


def run_validator(
    folder: Path,
    report: Path = REPORT_FIXTURE,
    delete_report: bool = False,
    vault_root: Path | None = None,
) -> tuple[int, dict]:
    command = [sys.executable, str(VALIDATOR), str(folder), "--report", str(report)]
    if vault_root is None:
        command.append("--fixture-mode")
    else:
        command += ["--vault-root", str(vault_root)]
    if delete_report:
        command.append("--delete-report-on-success")
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, json.loads(result.stdout)


class ValidateOutputTests(unittest.TestCase):
    def test_valid_fixture_passes(self):
        code, result = run_validator(FIXTURE)
        self.assertEqual(code, 0)
        self.assertTrue(result["valid"])

    def test_source_original_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            (folder / "source.pdf").write_bytes(b"synthetic invalid fixture")
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("source originals" in item for item in result["errors"]))

    def test_page_marker_out_of_range_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            note = folder / "sample.md"
            note.write_text(note.read_text().replace("source-page: 2", "source-page: 3"))
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("outside 1..2" in item for item in result["errors"]))

    def test_dangling_canvas_edge_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            canvas_path = folder / "sample.canvas"
            canvas = json.loads(canvas_path.read_text())
            canvas["edges"][0]["toNode"] = "ffffffffffffffff"
            canvas_path.write_text(json.dumps(canvas))
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("dangling toNode" in item for item in result["errors"]))

    def test_temporary_report_is_deleted_on_success(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            report = Path(temp) / "staging" / "conversion-report.md"
            shutil.copytree(FIXTURE, folder)
            report.parent.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            code, result = run_validator(folder, report, delete_report=True)
            self.assertEqual(code, 0)
            self.assertTrue(result["report_deleted"])
            self.assertFalse(report.exists())

    def test_report_inside_document_folder_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            report = folder / "conversion-report.md"
            shutil.copy2(REPORT_FIXTURE, report)
            code, result = run_validator(folder, report)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("outside the document folder" in item for item in result["errors"]))

    def test_vault_relative_canvas_path_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            vault = base / "vault"
            folder = vault / "COURSE101/Lectures/sample"
            report = base / "staging/conversion-report.md"
            shutil.copytree(FIXTURE, folder)
            report.parent.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            canvas_path = folder / "sample.canvas"
            canvas = json.loads(canvas_path.read_text())
            canvas["nodes"][0]["file"] = "COURSE101/Lectures/sample/sample.md"
            canvas_path.write_text(json.dumps(canvas))
            code, result = run_validator(folder, report, vault_root=vault)
            self.assertEqual(code, 0)
            self.assertTrue(result["valid"])

    def test_bare_canvas_filename_fails_with_vault_root(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            vault = base / "vault"
            folder = vault / "COURSE101/Lectures/sample"
            report = base / "staging/conversion-report.md"
            shutil.copytree(FIXTURE, folder)
            report.parent.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            code, result = run_validator(folder, report, vault_root=vault)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("file node unresolved" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
