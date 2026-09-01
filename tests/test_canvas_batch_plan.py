import importlib.util
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/plan-canvas-batch.py"
SPEC = importlib.util.spec_from_file_location("plan_canvas_batch", SCRIPT)
PLANNER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
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


class CanvasBatchPlanTests(unittest.TestCase):
    def test_one_item_does_not_force_spawn(self):
        plan = PLANNER.plan_batch({"schema_version": 1, "items": [item(1)]}, 4)
        self.assertFalse(plan["spawn_required"])
        self.assertEqual(plan["strategy"], "direct-or-single-subagent")

    def test_two_items_require_one_subagent_each(self):
        plan = PLANNER.plan_batch({"schema_version": 1, "items": [item(1), item(2)]}, 4)
        self.assertTrue(plan["spawn_required"])
        self.assertEqual(plan["strategy"], "one-subagent-per-document")
        self.assertEqual(len(plan["subagent_tasks"]), 2)
        self.assertEqual(plan["authoring_waves"], [["lesson-1", "lesson-2"]])
        self.assertEqual(plan["renderer_parallelism"], 1)

    def test_capacity_creates_waves_without_merging_files(self):
        plan = PLANNER.plan_batch(
            {"schema_version": 1, "items": [item(index) for index in range(1, 6)]},
            2,
        )
        self.assertEqual(plan["authoring_waves"], [
            ["lesson-1", "lesson-2"],
            ["lesson-3", "lesson-4"],
            ["lesson-5"],
        ])
        self.assertEqual(len(plan["subagent_tasks"]), 5)
        self.assertEqual(plan["renderer_order"], [f"lesson-{index}" for index in range(1, 6)])

    def test_shared_staging_path_is_rejected(self):
        first, second = item(1), item(2)
        second["staging"] = first["staging"]
        with self.assertRaisesRegex(PLANNER.BatchPlanError, "collides"):
            PLANNER.plan_batch({"schema_version": 1, "items": [first, second]}, 2)


if __name__ == "__main__":
    unittest.main()
