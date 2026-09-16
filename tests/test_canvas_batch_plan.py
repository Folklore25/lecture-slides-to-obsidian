import importlib.util
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/plan-canvas-batch.py"
SPEC = importlib.util.spec_from_file_location("plan_canvas_batch", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PLANNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLANNER)


def item(index: int) -> dict:
    slug = f"lesson-{index}"
    return {
        "id": slug,
        "note": f"/tmp/vault/{slug}/{slug}.md",
        "recall_model": f"/tmp/staging/{slug}/recall-model.json",
        "canvas": f"/tmp/vault/{slug}/{slug}.canvas",
        "staging": f"/tmp/staging/{slug}",
        "assets": f"/tmp/vault/{slug}/assets",
        "profile": "lecture-notes",
        "overwrite": False,
    }


class CanvasLaneTests(unittest.TestCase):
    def test_a_single_canvas_still_uses_the_serial_lane(self):
        plan = PLANNER.plan_batch({"schema_version": 1, "items": [item(1)]})
        self.assertEqual(plan["canvas_lane"]["owner"], "main-agent")
        self.assertEqual(plan["canvas_lane"]["parallelism"], 1)
        self.assertEqual(plan["canvas_lane"]["exclusive_resource"], "obsidian-app-gui")
        self.assertEqual(plan["canvas_lane"]["order"], ["lesson-1"])

    def test_many_canvases_are_never_fanned_out(self):
        plan = PLANNER.plan_batch(
            {"schema_version": 1, "items": [item(index) for index in range(1, 6)]}
        )
        self.assertEqual(plan["item_count"], 5)
        self.assertEqual(plan["canvas_lane"]["parallelism"], 1)
        self.assertTrue(plan["fan_out_forbidden"])
        self.assertFalse("authoring_parallelism" in plan)
        self.assertFalse("authoring_waves" in plan)
        self.assertFalse("spawn_required" in plan)
        self.assertEqual(
            plan["canvas_lane"]["order"], [f"lesson-{index}" for index in range(1, 6)]
        )
        self.assertEqual(len(plan["tasks"]), 5)

    def test_every_canvas_keeps_isolated_paths(self):
        plan = PLANNER.plan_batch(
            {"schema_version": 1, "items": [item(1), item(2)]}
        )
        self.assertTrue(plan["isolation_verified"])
        self.assertTrue(plan["merge_forbidden"])
        staging = {task["staging"] for task in plan["tasks"]}
        self.assertEqual(len(staging), 2)

    def test_shared_staging_path_is_rejected(self):
        first, second = item(1), item(2)
        second["staging"] = first["staging"]
        with self.assertRaisesRegex(PLANNER.BatchPlanError, "collides"):
            PLANNER.plan_batch({"schema_version": 1, "items": [first, second]})

    def test_shared_canvas_path_is_rejected(self):
        first, second = item(1), item(2)
        second["canvas"] = first["canvas"]
        with self.assertRaisesRegex(PLANNER.BatchPlanError, "collides"):
            PLANNER.plan_batch({"schema_version": 1, "items": [first, second]})

    def test_missing_field_is_rejected(self):
        broken = item(1)
        del broken["recall_model"]
        with self.assertRaisesRegex(PLANNER.BatchPlanError, "missing fields"):
            PLANNER.plan_batch({"schema_version": 1, "items": [broken]})

    def test_empty_batch_is_rejected(self):
        with self.assertRaisesRegex(PLANNER.BatchPlanError, "at least one Canvas"):
            PLANNER.plan_batch({"schema_version": 1, "items": []})


if __name__ == "__main__":
    unittest.main()
