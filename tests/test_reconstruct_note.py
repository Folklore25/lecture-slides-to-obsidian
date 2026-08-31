import importlib.util
import json
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/reconstruct-note.py"
FIXTURE = REPO / "tests/fixtures/synthetic/content-list-v2-policy.json"
SPEC = importlib.util.spec_from_file_location("reconstruct_note", SCRIPT)
RECONSTRUCT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RECONSTRUCT)


class ReconstructNoteTests(unittest.TestCase):
    def setUp(self):
        self.pages = json.loads(FIXTURE.read_text())
        self.metadata = {
            "title": "Example Policy Document",
            "course": "COURSE101",
            "source_filename": "example-policy.pdf",
            "source_sha256": "0" * 64,
            "mineru_model": "vlm",
            "status": "pre-class",
        }

    def test_policy_state_machine_distinguishes_overview_and_category(self):
        note, context = RECONSTRUCT.reconstruct(self.pages, self.metadata, "policy-document")
        self.assertIn("## Overview", note)
        self.assertIn("**1. Do not plagiarize.**", note)
        self.assertIn("## Category One", note)
        self.assertIn("### 1. Do not plagiarize.", note)
        self.assertEqual(note.count("### 1. Do not plagiarize."), 1)
        self.assertEqual(context["inventory"]["page_footnote"], 1)

    def test_page_count_and_markers_come_from_v2_groups(self):
        note, context = RECONSTRUCT.reconstruct(self.pages, self.metadata, "policy-document")
        self.assertIn("source_pages: 2", note)
        self.assertIn("<!-- source-page: 1 -->", note)
        self.assertIn("<!-- source-page: 2 -->", note)
        self.assertEqual(context["page_count_source"], "content_list_v2 length")

    def test_lecture_profile_adds_in_class_notes(self):
        note, _ = RECONSTRUCT.reconstruct(self.pages, self.metadata, "lecture-notes")
        self.assertTrue(note.rstrip().endswith("## In-class notes"))


if __name__ == "__main__":
    unittest.main()
