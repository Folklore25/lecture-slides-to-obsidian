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


def run_validator(folder: Path) -> tuple[int, dict]:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(folder)],
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


if __name__ == "__main__":
    unittest.main()
