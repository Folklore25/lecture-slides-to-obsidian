import hashlib
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
    recall_model: Path | None = None,
    render_metrics: Path | None = None,
    render_check: Path | None = None,
) -> tuple[int, dict]:
    command = [sys.executable, str(VALIDATOR), str(folder), "--report", str(report)]
    if vault_root is None:
        command.append("--fixture-mode")
    else:
        command += ["--vault-root", str(vault_root)]
    if recall_model is not None:
        command += ["--recall-model", str(recall_model)]
    if render_metrics is not None:
        command += ["--render-metrics", str(render_metrics)]
    if render_check is not None:
        command += ["--render-check", str(render_check)]
    if delete_report:
        command.append("--delete-report-on-success")
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, json.loads(result.stdout)


def write_render_qa(staging: Path, canvas: Path) -> tuple[Path, Path]:
    metrics = staging / "canvas-render-metrics.json"
    check = staging / "canvas-render-check.json"
    metrics.write_text(json.dumps({
        "schema_version": 1,
        "mode": "measure",
        "measurement_complete": True,
        "nodes": [{"id": "synthetic", "required_height": 300}],
    }))
    check.write_text(json.dumps({
        "schema_version": 1,
        "mode": "check",
        "measurement_complete": True,
        "valid": True,
        "canvas_sha256": hashlib.sha256(canvas.read_bytes()).hexdigest(),
    }))
    return metrics, check


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

    def test_generic_canvas_relation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            canvas_path = folder / "sample.canvas"
            canvas = json.loads(canvas_path.read_text())
            concept_ids = {
                node["id"] for node in canvas["nodes"]
                if "<!-- recall-map: concept -->" in node.get("text", "")
            }
            semantic_edge = next(
                edge for edge in canvas["edges"]
                if edge["fromNode"] in concept_ids and edge["toNode"] in concept_ids
            )
            semantic_edge["label"] = "related to"
            canvas_path.write_text(json.dumps(canvas))
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("structural/generic label" in item for item in result["errors"]))

    def test_missing_one_minute_overview_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            canvas_path = folder / "sample.canvas"
            canvas = json.loads(canvas_path.read_text())
            overview = next(
                node for node in canvas["nodes"]
                if "<!-- recall-map: overview -->" in node.get("text", "")
            )
            overview["text"] = overview["text"].replace("<!-- recall-map: overview -->", "")
            canvas_path.write_text(json.dumps(canvas))
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("exactly one overview" in item for item in result["errors"]))

    def test_stale_render_check_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            folder = base / "document"
            staging = base / "staging"
            report = staging / "conversion-report.md"
            shutil.copytree(FIXTURE, folder)
            staging.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            render_metrics, render_check = write_render_qa(staging, folder / "sample.canvas")
            check = json.loads(render_check.read_text())
            check["canvas_sha256"] = "0" * 64
            render_check.write_text(json.dumps(check))
            code, result = run_validator(
                folder, report, render_metrics=render_metrics, render_check=render_check
            )
            self.assertNotEqual(code, 0)
            self.assertTrue(any("does not match the delivered Canvas" in item for item in result["errors"]))

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

    def test_standardized_asset_name_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            (folder / "assets/page-001-figure-01.png").write_bytes(b"synthetic")
            code, result = run_validator(folder)
            self.assertEqual(code, 0)
            self.assertTrue(result["valid"])

    def test_unstandardized_asset_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            (folder / "assets/figure.png").write_bytes(b"synthetic")
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("page-PPP-kind-NN.ext" in item for item in result["errors"]))

    def test_asset_sequence_gap_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            (folder / "assets/page-001-figure-01.png").write_bytes(b"synthetic")
            (folder / "assets/page-001-figure-03.png").write_bytes(b"synthetic")
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("contiguous from 01" in item for item in result["errors"]))

    def test_vault_relative_canvas_path_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            vault = base / "vault"
            folder = vault / "COURSE101/Lectures/sample"
            report = base / "staging/conversion-report.md"
            recall_model = base / "staging/recall-model.json"
            shutil.copytree(FIXTURE, folder)
            report.parent.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            recall_model.write_text('{"schema_version":1}')
            canvas_path = folder / "sample.canvas"
            canvas = json.loads(canvas_path.read_text())
            note_node = next(
                node for node in canvas["nodes"]
                if node.get("type") == "file" and node.get("file", "").endswith(".md")
            )
            note_node["file"] = "COURSE101/Lectures/sample/sample.md"
            canvas_path.write_text(json.dumps(canvas))
            render_metrics, render_check = write_render_qa(report.parent, canvas_path)
            code, result = run_validator(
                folder, report, vault_root=vault, recall_model=recall_model,
                render_metrics=render_metrics, render_check=render_check,
            )
            self.assertEqual(code, 0)
            self.assertTrue(result["valid"])

    def test_bare_canvas_filename_fails_with_vault_root(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            vault = base / "vault"
            folder = vault / "COURSE101/Lectures/sample"
            report = base / "staging/conversion-report.md"
            recall_model = base / "staging/recall-model.json"
            shutil.copytree(FIXTURE, folder)
            report.parent.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            recall_model.write_text('{"schema_version":1}')
            render_metrics, render_check = write_render_qa(report.parent, folder / "sample.canvas")
            code, result = run_validator(
                folder, report, vault_root=vault, recall_model=recall_model,
                render_metrics=render_metrics, render_check=render_check,
            )
            self.assertNotEqual(code, 0)
            self.assertTrue(any("file node unresolved" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
