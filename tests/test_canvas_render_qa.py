import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/obsidian-canvas-designer/scripts/canvas-render-qa.py"
SPEC = importlib.util.spec_from_file_location("canvas_render_qa", SCRIPT)
RENDER_QA = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RENDER_QA)


PROFILE = {
    "profile_id": "test-profile",
    "requires_foreground": True,
    "obsidian_version": "1.13.7",
    "installer_version": "1.12.4",
    "screen_css_width": 1512,
    "screen_css_height": 982,
    "device_pixel_ratio": 2,
    "theme": "Composer",
    "base_font_size": 16,
    "canvas_font_size_px": 16,
    "canvas_line_height_px": 27.2,
    "sidebar_font_size_px": 13,
    "minimum_effective_font_px": 13,
    "reading_zoom": 0,
    "vertical_chrome_px": 34,
    "safety_margin_px": 8,
    "minimum_headroom_px": 8,
    "maximum_headroom_px": 12,
    "round_to_px": 4,
    "top_lane_to_modules_gap_px": 80,
}


class CanvasRenderQaTests(unittest.TestCase):
    def test_bundled_profile_matches_measured_workstation(self):
        profile = json.loads(RENDER_QA.DEFAULT_PROFILE.read_text())
        self.assertEqual(profile["screen_css_width"], 1512)
        self.assertEqual(profile["screen_css_height"], 982)
        self.assertEqual(profile["theme"], "Composer")
        self.assertEqual(profile["canvas_font_size_px"], 16)
        self.assertEqual(profile["sidebar_font_size_px"], 13)
        self.assertEqual(profile["vertical_chrome_px"], 34)
        self.assertEqual(profile["safety_margin_px"], 8)
        self.assertEqual(profile["minimum_headroom_px"], 8)
        self.assertEqual(profile["maximum_headroom_px"], 12)
        self.assertEqual(profile["top_lane_to_modules_gap_px"], 80)
        self.assertTrue(profile["requires_foreground"])

    def test_measured_screenshot_cards_round_to_safe_heights(self):
        self.assertEqual(RENDER_QA.rounded_required_height(525, 34, 8, 4), 568)
        self.assertEqual(RENDER_QA.rounded_required_height(434, 34, 8, 4), 476)
        self.assertEqual(RENDER_QA.rounded_required_height(436, 34, 8, 4), 480)

    def test_check_requires_profile_margin_not_just_no_clipping(self):
        with tempfile.TemporaryDirectory() as temp:
            canvas = Path(temp) / "sample.canvas"
            canvas.write_text('{"nodes":[],"edges":[]}')
            measured = {
                **{key: value for key, value in PROFILE.items() if key not in {
                    "profile_id", "minimum_effective_font_px", "reading_zoom",
                    "vertical_chrome_px", "safety_margin_px", "round_to_px"
                }},
                "document_has_focus": True,
                "nodes": [
                    {
                        "id": "0123456789abcdef",
                        "text": "## Concept\nBody",
                        "width": 420,
                        "height": 560,
                        "max_child_bottom": 525,
                    }
                ],
            }
            result = RENDER_QA.build_result(canvas, PROFILE, measured, "check")
            self.assertFalse(result["valid"])
            self.assertEqual(result["clipped_nodes"], [])
            self.assertEqual(result["nodes_below_profile_margin"], ["0123456789abcdef"])

    def test_check_rejects_excessive_card_headroom(self):
        with tempfile.TemporaryDirectory() as temp:
            canvas = Path(temp) / "sample.canvas"
            canvas.write_text('{"nodes":[],"edges":[]}')
            measured = {
                **{key: value for key, value in PROFILE.items() if key not in {
                    "profile_id", "minimum_effective_font_px", "reading_zoom",
                    "vertical_chrome_px", "safety_margin_px", "round_to_px",
                    "minimum_headroom_px", "maximum_headroom_px",
                }},
                "document_has_focus": True,
                "reading_view": {"zoom": 0},
                "nodes": [{
                    "id": "0123456789abcdef",
                    "text": "## Concept\nBody",
                    "width": 420,
                    "height": 700,
                    "max_child_bottom": 525,
                }],
            }
            result = RENDER_QA.build_result(canvas, PROFILE, measured, "check")
            self.assertFalse(result["valid"])
            self.assertEqual(result["nodes_above_maximum_headroom"], ["0123456789abcdef"])

    def test_environment_mismatch_fails_closed(self):
        measured = {
            **{key: value for key, value in PROFILE.items() if key not in {
                "profile_id", "minimum_effective_font_px", "reading_zoom",
                "vertical_chrome_px", "safety_margin_px", "round_to_px"
            }},
            "document_has_focus": True,
            "theme": "Different theme",
        }
        errors = RENDER_QA.environment_errors(PROFILE, measured)
        self.assertTrue(any("theme" in item for item in errors))

    def test_final_check_rejects_top_lane_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            canvas = Path(temp) / "sample.canvas"
            canvas.write_text(json.dumps({
                "nodes": [
                    {"id":"overview","type":"text","x":0,"y":0,"width":800,"height":470,
                     "text":"<!-- recall-map: overview -->\n# Recall"},
                    {"id":"source","type":"file","x":880,"y":0,"width":420,"height":470,"file":"note.md"},
                    {"id":"module","type":"group","x":0,"y":520,"width":520,"height":500,"label":"01 · Module"},
                ],
                "edges": [],
            }))
            measured = {
                **{key: value for key, value in PROFILE.items() if key not in {
                    "profile_id", "minimum_effective_font_px", "reading_zoom",
                    "vertical_chrome_px", "safety_margin_px", "round_to_px",
                    "top_lane_to_modules_gap_px",
                }},
                "document_has_focus": True,
                "reading_view": {"zoom": 0},
                "nodes": [{
                    "id": "overview", "text": "<!-- recall-map: overview -->\n# Recall",
                    "width": 800, "height": 470, "max_child_bottom": 400,
                }],
            }
            result = RENDER_QA.build_result(canvas, PROFILE, measured, "check")
            self.assertFalse(result["valid"])
            self.assertEqual(result["top_lane_to_modules_gap"], 50)
            self.assertTrue(any("requires at least 80px" in item for item in result["layout_errors"]))


if __name__ == "__main__":
    unittest.main()
