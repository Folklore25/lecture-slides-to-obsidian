import importlib.util
import json
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/obsidian-canvas-designer/scripts/canvas-aesthetic-qa.py"
FIXTURE = REPO / "tests/fixtures/synthetic/valid-document-folder/sample.canvas"
SPEC = importlib.util.spec_from_file_location("canvas_aesthetic_qa", SCRIPT)
AESTHETIC = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(AESTHETIC)


class CanvasAestheticQaTests(unittest.TestCase):
    def test_generated_fixture_passes_axton_informed_gates(self):
        result = AESTHETIC.score_canvas(json.loads(FIXTURE.read_text()))
        self.assertTrue(result["valid"])
        self.assertGreaterEqual(result["score"], 85)
        self.assertEqual(result["edge_crossings"], 0)

    def test_repeated_recall_cue_fails_density_contract(self):
        canvas = json.loads(FIXTURE.read_text())
        concept = next(
            node for node in canvas["nodes"]
            if "<!-- recall-map: concept -->" in node.get("text", "")
        )
        concept["text"] += "\n\n**Recall cue:** This should be consolidated."
        result = AESTHETIC.score_canvas(canvas)
        self.assertFalse(result["valid"])
        self.assertTrue(any("repeats a recall cue" in item for item in result["hard_errors"]))

    def test_semantic_color_mismatch_fails(self):
        canvas = json.loads(FIXTURE.read_text())
        concept = next(
            node for node in canvas["nodes"]
            if "<!-- recall-kind: foundation -->" in node.get("text", "")
        )
        concept["color"] = "1"
        result = AESTHETIC.score_canvas(canvas)
        self.assertFalse(result["valid"])
        self.assertTrue(any("color does not match" in item for item in result["hard_errors"]))

    def test_top_orientation_lane_requires_group_label_clearance(self):
        canvas = json.loads(FIXTURE.read_text())
        groups = [node for node in canvas["nodes"] if node.get("type") == "group"]
        overview = next(
            node for node in canvas["nodes"]
            if "<!-- recall-map: overview -->" in node.get("text", "")
        )
        outside_file = next(
            node for node in canvas["nodes"]
            if node.get("type") == "file"
            and not any(AESTHETIC.contains(group, node) for group in groups)
        )
        module_top = min(group["y"] for group in groups)
        overview["height"] = module_top - overview["y"] - 50
        outside_file["height"] = module_top - outside_file["y"] - 50
        result = AESTHETIC.score_canvas(canvas)
        self.assertFalse(result["valid"])
        self.assertEqual(result["top_lane_to_modules_gap"], 50)
        self.assertTrue(any("upward-rendered group labels" in item for item in result["hard_errors"]))


if __name__ == "__main__":
    unittest.main()
