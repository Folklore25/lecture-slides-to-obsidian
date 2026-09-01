import importlib.util
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-asr-enricher/scripts/validate-enrichment-plan.py"
SPEC = importlib.util.spec_from_file_location("validate_enrichment_plan", SCRIPT)
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VALIDATOR)


def entry(**overrides) -> dict:
    value = {
        "id": "teacher-20260901-001",
        "actor": "teacher",
        "kind": "example",
        "target_heading": "Core concept",
        "target_level": 2,
        "body": "The lecturer used a queue to illustrate the bottleneck.",
        "source_anchor": "00:31:24",
        "evidence": "The queue stops the rest of the process from moving faster.",
        "novelty_basis": "new-example",
        "confidence": "high",
        "apply": True,
        "routing_status": "matched",
    }
    value.update(overrides)
    return value


def plan(entries) -> dict:
    return {
        "schema_version": 1,
        "note": "COURSE101/Lectures/example/example.md",
        "asr_source": "teacher-session.md",
        "entries": entries,
        "no_additions_reason": None,
    }


class AsrEnrichmentPlanTests(unittest.TestCase):
    def test_valid_plan_emits_teacher_insertion_patch(self):
        patch, review = VALIDATOR.validate_plan(plan([entry()]))
        self.assertEqual(review, [])
        self.assertEqual(len(patch["entries"]), 1)
        self.assertEqual(patch["entries"][0]["actor"], "teacher")
        self.assertNotIn("evidence", patch["entries"][0])

    def test_low_confidence_entry_cannot_apply(self):
        with self.assertRaisesRegex(VALIDATOR.PlanError, "low-confidence"):
            VALIDATOR.validate_plan(plan([entry(confidence="low", apply=True)]))

    def test_review_entry_is_not_emitted_for_application(self):
        patch, review = VALIDATOR.validate_plan(plan([entry(apply=False, confidence="medium")]))
        self.assertEqual(patch["entries"], [])
        self.assertEqual(len(review), 1)
        self.assertIn("evidence", review[0])

    def test_empty_plan_requires_reason(self):
        with self.assertRaisesRegex(VALIDATOR.PlanError, "no_additions_reason"):
            VALIDATOR.validate_plan(plan([]))

    def test_duplicate_addition_is_rejected(self):
        second = entry(id="teacher-20260901-002")
        with self.assertRaisesRegex(VALIDATOR.PlanError, "duplicates"):
            VALIDATOR.validate_plan(plan([entry(), second]))


if __name__ == "__main__":
    unittest.main()
