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
    def test_lane_is_lease_guarded_not_serialized_by_policy(self):
        plan = PLANNER.plan_batch({"schema_version": 1, "items": [item(1)]})
        lane = plan["canvas_lane"]
        self.assertEqual(lane["authoring_parallelism"], "unbounded")
        self.assertEqual(lane["dom_step_guard"], "exclusive-lease")
        self.assertEqual(lane["lease_name"], "obsidian-gui")
        self.assertEqual(lane["lease_tool"], "scripts/obsidian-gui-lock.py")
        self.assertFalse(lane["focus_required"])
        self.assertTrue(lane["queues_instead_of_failing"])
        self.assertEqual(lane["order"], ["lesson-1"])

    def test_many_canvases_are_allowed_but_the_dom_step_stays_single_lane(self):
        plan = PLANNER.plan_batch(
            {"schema_version": 1, "items": [item(index) for index in range(1, 6)]}
        )
        self.assertEqual(plan["item_count"], 5)
        self.assertEqual(plan["canvas_lane"]["dom_step_concurrency"], 1)
        self.assertFalse("fan_out_forbidden" in plan)
        self.assertEqual(
            plan["canvas_lane"]["order"], [f"lesson-{index}" for index in range(1, 6)]
        )
        self.assertEqual(len(plan["tasks"]), 5)

    def test_every_canvas_keeps_isolated_paths(self):
        plan = PLANNER.plan_batch({"schema_version": 1, "items": [item(1), item(2)]})
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

    def test_shared_recall_model_path_is_rejected(self):
        first, second = item(1), item(2)
        second["recall_model"] = first["recall_model"]
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
