import importlib.util
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/plan-conversion-batch.py"
SPEC = importlib.util.spec_from_file_location("plan_conversion_batch", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PLANNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLANNER)


def item(index: int) -> dict:
    slug = f"lesson-{index}"
    return {
        "id": slug,
        "source": f"/external/{slug}.pdf",
        "document_folder": f"/tmp/vault/COURSE101/Lectures/{slug}",
        "staging": f"/tmp/convert-{slug}",
        "profile": "lecture-notes",
    }


def manifest(*indexes: int) -> dict:
    return {"schema_version": 1, "items": [item(index) for index in indexes]}


class ConversionDispatchTests(unittest.TestCase):
    def test_a_single_file_is_converted_directly(self):
        plan = PLANNER.plan_batch(manifest(1), 4)
        self.assertEqual(plan["file_count"], 1)
        self.assertFalse(plan["dispatch_required"])
        self.assertEqual(plan["strategy"], "direct")
        self.assertEqual(plan["waves"], [["lesson-1"]])

    def test_two_files_require_one_subagent_each(self):
        plan = PLANNER.plan_batch(manifest(1, 2), 4)
        self.assertTrue(plan["dispatch_required"])
        self.assertEqual(plan["strategy"], "one-subagent-per-file")
        self.assertEqual(len(plan["subagent_tasks"]), 2)
        self.assertEqual(plan["waves"], [["lesson-1", "lesson-2"]])

    def test_capacity_creates_waves_without_merging_files(self):
        plan = PLANNER.plan_batch(manifest(1, 2, 3, 4, 5), 2)
        self.assertEqual(
            plan["waves"],
            [["lesson-1", "lesson-2"], ["lesson-3", "lesson-4"], ["lesson-5"]],
        )
        self.assertEqual(len(plan["subagent_tasks"]), 5)

    def test_shared_state_stays_with_the_main_agent(self):
        plan = PLANNER.plan_batch(manifest(1, 2), 4)
        self.assertEqual(plan["shared_state_owner"], "main-agent")
        self.assertIn("course-registry", plan["shared_state"])

    def test_canvas_dom_steps_are_lease_guarded_not_forbidden(self):
        plan = PLANNER.plan_batch(manifest(1, 2), 4)
        lane = plan["canvas_lane"]
        self.assertEqual(lane["authoring_parallelism"], "unbounded")
        self.assertEqual(lane["dom_step_guard"], "exclusive-lease")
        self.assertEqual(lane["lease_name"], "obsidian-gui")
        for task in plan["subagent_tasks"]:
            self.assertIn("Canvas files", task["returns"])
            self.assertEqual(
                task["must_not"], "write outside its own document folder and staging directory"
            )

    def test_duplicate_source_is_rejected(self):
        first, second = item(1), item(2)
        second["source"] = first["source"]
        with self.assertRaisesRegex(PLANNER.BatchPlanError, "collides"):
            PLANNER.plan_batch({"schema_version": 1, "items": [first, second]}, 2)

    def test_duplicate_document_folder_is_rejected(self):
        first, second = item(1), item(2)
        second["document_folder"] = first["document_folder"]
        with self.assertRaisesRegex(PLANNER.BatchPlanError, "collides"):
            PLANNER.plan_batch({"schema_version": 1, "items": [first, second]}, 2)

    def test_unsupported_profile_is_rejected(self):
        broken = item(1)
        broken["profile"] = "slides"
        with self.assertRaisesRegex(PLANNER.BatchPlanError, "profile is unsupported"):
            PLANNER.plan_batch({"schema_version": 1, "items": [broken]}, 2)

    def test_vault_containment_is_enforced(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            vault = Path(temp) / "vault"
            vault.mkdir()
            bad_source = vault / "inside.pdf"
            bad_source.write_bytes(b"synthetic")
            inside = item(1)
            inside["source"] = str(bad_source)
            inside["document_folder"] = str(vault / "COURSE101/Lectures/lesson-1")
            with self.assertRaisesRegex(PLANNER.BatchPlanError, "outside the vault"):
                PLANNER.plan_batch({"schema_version": 1, "items": [inside]}, 2, vault)

            outside = item(1)
            outside["document_folder"] = "/tmp/not-the-vault/lesson-1"
            with self.assertRaisesRegex(PLANNER.BatchPlanError, "inside the vault"):
                PLANNER.plan_batch({"schema_version": 1, "items": [outside]}, 2, vault)

            staging_in_vault = item(1)
            staging_in_vault["document_folder"] = str(vault / "COURSE101/Lectures/lesson-1")
            staging_in_vault["staging"] = str(vault / "tmp")
            with self.assertRaisesRegex(PLANNER.BatchPlanError, "staging must stay outside"):
                PLANNER.plan_batch({"schema_version": 1, "items": [staging_in_vault]}, 2, vault)

    def test_missing_field_is_rejected(self):
        broken = item(1)
        del broken["staging"]
        with self.assertRaisesRegex(PLANNER.BatchPlanError, "missing fields"):
            PLANNER.plan_batch({"schema_version": 1, "items": [broken]}, 2)


if __name__ == "__main__":
    unittest.main()
