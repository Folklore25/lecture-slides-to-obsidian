import importlib.util
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/obsidian-canvas-designer/scripts/recall-skeleton.py"
NOTE = REPO / "tests/fixtures/synthetic/valid-document-folder/sample.md"
SPEC = importlib.util.spec_from_file_location("recall_skeleton", SCRIPT)
SKELETON = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SKELETON)


class RecallSkeletonTests(unittest.TestCase):
    def test_inventory_builds_exact_h2_page_coverage(self):
        inspection = SKELETON.inspect_note(NOTE.read_text())
        self.assertEqual(inspection["hard_errors"], [])
        self.assertEqual(
            [(item["heading"], item["source_page"]) for item in inspection["h2_sections"]],
            [
                ("Core components", 1),
                ("How feedback works", 2),
                ("Applications and limits", 2),
                ("In-class notes", 2),
            ],
        )
        draft = SKELETON.create_skeleton(inspection, "lecture-notes", "pre-class")
        self.assertEqual(draft["draft_status"], "authoring-required")
        self.assertEqual(len(draft["coverage"]), 4)
        self.assertEqual(draft["concepts"], [])

    def test_h3_only_note_fails_without_modifying_it(self):
        text = "# Topic\n\n<!-- source-page: 1 -->\n\n### Candidate section\n\nBody.\n"
        inspection = SKELETON.inspect_note(text)
        self.assertTrue(any("No H2 sections" in item for item in inspection["hard_errors"]))
        self.assertEqual(inspection["h3_review_candidates"][0]["heading"], "Candidate section")
        self.assertEqual(text.splitlines()[4], "### Candidate section")

    def test_duplicate_heading_page_anchor_is_reported(self):
        text = (
            "---\nsource_pages: 1\nconversion_profile: lecture-notes\n---\n# Topic\n"
            "<!-- source-page: 1 -->\n## Repeated\nBody.\n## Repeated\nMore.\n"
        )
        inspection = SKELETON.inspect_note(text)
        self.assertTrue(any("Duplicate H2" in item for item in inspection["hard_errors"]))


if __name__ == "__main__":
    unittest.main()
