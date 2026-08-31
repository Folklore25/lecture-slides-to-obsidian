import importlib.util
import re
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/build-canvas.py"
SPEC = importlib.util.spec_from_file_location("build_canvas", SCRIPT)
BUILD_CANVAS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILD_CANVAS)


class BuildCanvasTests(unittest.TestCase):
    def test_paths_are_complete_vault_relative_and_ids_are_stable(self):
        with tempfile.TemporaryDirectory() as temp:
            vault = Path(temp) / "vault"
            folder = vault / "IS6000/Lectures/l01-code-of-conduct"
            assets = folder / "assets"
            assets.mkdir(parents=True)
            note = folder / "l01-code-of-conduct.md"
            note.write_text("# Code of Conduct\n\n## Overview\n\nText.\n\n## Category One\n\nRule.\n")
            (assets / "page-004-figure-01.png").write_bytes(b"synthetic")
            first = BUILD_CANVAS.build_canvas(note, vault, "policy-document", assets)
            second = BUILD_CANVAS.build_canvas(note, vault, "policy-document", assets)
            self.assertEqual(first, second)
            file_nodes = [node for node in first["nodes"] if node["type"] == "file"]
            paths = {node["file"] for node in file_nodes}
            self.assertIn(
                "IS6000/Lectures/l01-code-of-conduct/l01-code-of-conduct.md",
                paths,
            )
            self.assertIn(
                "IS6000/Lectures/l01-code-of-conduct/assets/page-004-figure-01.png",
                paths,
            )
            all_ids = [item["id"] for item in first["nodes"] + first["edges"]]
            self.assertEqual(len(all_ids), len(set(all_ids)))
            self.assertTrue(all(re.fullmatch(r"[0-9a-f]{16}", value) for value in all_ids))

    def test_note_outside_vault_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            vault = base / "vault"
            vault.mkdir()
            note = base / "outside.md"
            note.write_text("# Outside\n")
            with self.assertRaises(BUILD_CANVAS.CanvasBuildError):
                BUILD_CANVAS.build_canvas(note, vault, "lecture-notes")


if __name__ == "__main__":
    unittest.main()
