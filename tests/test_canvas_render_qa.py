import importlib.util
import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/obsidian-canvas-designer/scripts/canvas-render-qa.py"
SPEC = importlib.util.spec_from_file_location("canvas_render_qa", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RENDER_QA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDER_QA)


def stub_obsidian_running(running: bool) -> None:
    """Point the renderer QA's precondition check at a fixed answer.

    The real check asks whether the Obsidian GUI is already up, because the CLI would
    otherwise cold-start the app and pop its window forward. setattr is used because the
    module is loaded from a path and has no static attribute list.
    """
    setattr(RENDER_QA, "obsidian_is_running", lambda: running)


stub_obsidian_running(True)


PROFILE = {
    "profile_id": "test-profile",
    "requires_foreground": False,
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


def measured_environment(**overrides) -> dict:
    base = {
        key: value for key, value in PROFILE.items()
        if key not in {
            "profile_id", "minimum_effective_font_px", "reading_zoom",
            "vertical_chrome_px", "safety_margin_px", "round_to_px",
        }
    }
    base["document_has_focus"] = False
    base.update(overrides)
    return base


class FakeLock:
    def __init__(self):
        self.acquired = 0

    @contextmanager
    def hold(self, vault_root, owner=None, timeout=120.0):
        self.acquired += 1
        yield {"owner": owner or "test", "waited_seconds": 0.0, "reentrant": False}


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

    def test_bundled_profile_treats_focus_as_a_diagnostic(self):
        profile = json.loads(RENDER_QA.DEFAULT_PROFILE.read_text())
        self.assertFalse(profile["requires_foreground"])
        self.assertEqual(profile["focus_policy"], "diagnostic-only")

    def test_unfocused_measurement_is_not_an_environment_error(self):
        errors = RENDER_QA.environment_errors(PROFILE, measured_environment())
        self.assertEqual([item for item in errors if "focus" in item], [])

    def test_a_profile_may_still_demand_foreground_explicitly(self):
        strict = {**PROFILE, "requires_foreground": True}
        errors = RENDER_QA.environment_errors(strict, measured_environment())
        self.assertTrue(any("foreground and focused" in item for item in errors))

    def test_qa_never_activates_the_obsidian_application(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"-a"', source)
        self.assertNotIn("'open'", source)

    def test_refuses_to_measure_when_obsidian_is_not_running(self):
        stub_obsidian_running(False)
        try:
            with self.assertRaises(RENDER_QA.RenderQaError) as caught:
                RENDER_QA.require_obsidian_running()
        finally:
            stub_obsidian_running(True)
        self.assertIn("Obsidian is not running", str(caught.exception))

    def test_measurement_takes_the_shared_gui_lease(self):
        lock = FakeLock()
        names = ("load_gui_lock", "canvas_is_open", "_measure_open_canvas")
        originals = {name: getattr(RENDER_QA, name) for name in names}
        try:
            setattr(RENDER_QA, "load_gui_lock", lambda: lock)
            setattr(RENDER_QA, "canvas_is_open", lambda relative, vault_root: True)
            setattr(RENDER_QA, "_measure_open_canvas", lambda relative, vault_root, profile, mode: {"nodes": []})
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                canvas = root / "sample.canvas"
                canvas.write_text('{"nodes":[],"edges":[]}')
                result = RENDER_QA.measure_canvas(canvas, root, PROFILE, "measure", "agent-a", 5)
        finally:
            for name, value in originals.items():
                setattr(RENDER_QA, name, value)
        self.assertEqual(lock.acquired, 1)
        self.assertEqual(result["gui_lease"]["owner"], "agent-a")
        self.assertFalse(result["gui_lease"]["opened_canvas_in_this_step"])

    def test_already_open_canvas_is_not_reopened(self):
        calls = []
        names = ("load_gui_lock", "canvas_is_open", "_measure_open_canvas", "run_cli")
        originals = {name: getattr(RENDER_QA, name) for name in names}
        try:
            setattr(RENDER_QA, "load_gui_lock", lambda: FakeLock())
            setattr(RENDER_QA, "canvas_is_open", lambda relative, vault_root: True)
            setattr(RENDER_QA, "_measure_open_canvas", lambda relative, vault_root, profile, mode: {"nodes": []})
            setattr(RENDER_QA, "run_cli", lambda arguments, cwd: calls.append(arguments) or "")
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                canvas = root / "sample.canvas"
                canvas.write_text('{"nodes":[],"edges":[]}')
                RENDER_QA.measure_canvas(canvas, root, PROFILE, "measure", "agent-a", 5)
        finally:
            for name, value in originals.items():
                setattr(RENDER_QA, name, value)
        self.assertEqual([call for call in calls if "open" in call], [])

    def test_wait_for_canvas_open_polls_until_mounted(self):
        calls = []
        original = RENDER_QA.canvas_is_open
        try:
            def fake_is_open(relative, vault_root):
                calls.append(1)
                return len(calls) >= 3

            setattr(RENDER_QA, "canvas_is_open", fake_is_open)
            self.assertTrue(RENDER_QA.wait_for_canvas_open("a.canvas", Path("/tmp"), 2.0, 0.01))
            self.assertEqual(len(calls), 3)
            calls.clear()
            setattr(RENDER_QA, "canvas_is_open", lambda relative, vault_root: False)
            self.assertFalse(RENDER_QA.wait_for_canvas_open("a.canvas", Path("/tmp"), 0.05, 0.01))
        finally:
            setattr(RENDER_QA, "canvas_is_open", original)

    def test_measured_screenshot_cards_round_to_safe_heights(self):
        self.assertEqual(RENDER_QA.rounded_required_height(525, 34, 8, 4), 568)
        self.assertEqual(RENDER_QA.rounded_required_height(434, 34, 8, 4), 476)
        self.assertEqual(RENDER_QA.rounded_required_height(436, 34, 8, 4), 480)

    def test_check_requires_profile_margin_not_just_no_clipping(self):
        with tempfile.TemporaryDirectory() as temp:
            canvas = Path(temp) / "sample.canvas"
            canvas.write_text('{"nodes":[],"edges":[]}')
            measured = {
                **measured_environment(),
                "nodes": [{
                    "id": "0123456789abcdef",
                    "text": "## Concept\nBody",
                    "width": 420,
                    "height": 560,
                    "max_child_bottom": 525,
                }],
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
                **measured_environment(),
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
        errors = RENDER_QA.environment_errors(
            PROFILE, measured_environment(theme="Different theme")
        )
        self.assertTrue(any("theme" in item for item in errors))

    def test_unreadable_canvas_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as temp:
            canvas = Path(temp) / "sample.canvas"
            canvas.write_text("not json")
            with self.assertRaisesRegex(RENDER_QA.RenderQaError, "cannot read the Canvas JSON"):
                RENDER_QA.build_result(canvas, PROFILE, measured_environment(), "measure")

    def test_final_check_rejects_top_lane_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            canvas = Path(temp) / "sample.canvas"
            canvas.write_text(json.dumps({
                "nodes": [
                    {"id":"overview","type":"text","x":0,"y":0,"width":800,"height":470,
                     "text":"<!-- recall-map: overview -->\n# Recall"},
                    {"id":"source","type":"file","x":880,"y":0,"width":420,"height":470,"file":"note.md"},
                    {"id":"module","type":"group","x":0,"y":520,"width":520,"height":500,"label":"01 - Module"},
                ],
                "edges": [],
            }))
            profile = {**PROFILE}
            profile.pop("top_lane_to_modules_gap_px")
            measured = {
                **measured_environment(),
                "reading_view": {"zoom": 0},
                "nodes": [{
                    "id": "overview", "text": "<!-- recall-map: overview -->\n# Recall",
                    "width": 800, "height": 470, "max_child_bottom": 400,
                }],
            }
            result = RENDER_QA.build_result(canvas, profile, measured, "check")
            self.assertFalse(result["valid"])
            self.assertEqual(result["top_lane_to_modules_gap"], 50)
            self.assertTrue(any("requires at least 80px" in item for item in result["layout_errors"]))


if __name__ == "__main__":
    unittest.main()
