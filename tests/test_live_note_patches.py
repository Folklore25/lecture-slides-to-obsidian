import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/obsidian-live-lecture-notes/scripts/apply-note-patches.py"
SPEC = importlib.util.spec_from_file_location("apply_note_patches", SCRIPT)
PATCHES = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PATCHES)


NOTE = """---
type: course-material
---
# Lesson

<!-- source-page: 1 -->

## Core concept

Source transcription remains here.

### Example

Source example remains here.

## In-class notes
"""


def student_entry(**overrides) -> dict:
    entry = {
        "id": "student-20260901T143022-001",
        "actor": "student",
        "kind": "connection",
        "target_heading": "Core concept",
        "target_level": 2,
        "body": "This connects the mechanism to an earlier constraint.",
        "captured_at": "2026-09-01T14:30:22+08:00",
        "routing_status": "matched",
    }
    entry.update(overrides)
    return entry


class LiveNotePatchTests(unittest.TestCase):
    def test_course_material_frontmatter_is_required_for_live_target(self):
        self.assertEqual(PATCHES.frontmatter_type(NOTE), "course-material")
        self.assertIsNone(PATCHES.frontmatter_type("# Ordinary note\n"))

    def test_inserts_layered_callout_without_rewriting_source(self):
        modified, outcomes = PATCHES.apply_entries(NOTE, [student_entry()])
        self.assertEqual(outcomes[0]["status"], "inserted")
        self.assertIn("Source transcription remains here.", modified)
        self.assertIn("Source example remains here.", modified)
        self.assertIn("<!-- source-page: 1 -->", modified)
        self.assertIn("[!note] In-class connection", modified)
        self.assertLess(modified.index("In-class connection"), modified.index("## In-class notes"))

    def test_retry_is_idempotent(self):
        once, _ = PATCHES.apply_entries(NOTE, [student_entry()])
        twice, outcomes = PATCHES.apply_entries(once, [student_entry()])
        self.assertEqual(once, twice)
        self.assertEqual(outcomes[0]["status"], "already_present")

    def test_ambiguous_heading_is_rejected(self):
        duplicate = NOTE.replace("## In-class notes", "## Core concept\n\nDuplicate.\n\n## In-class notes")
        with self.assertRaisesRegex(PATCHES.PatchError, "ambiguous"):
            PATCHES.apply_entries(duplicate, [student_entry()])

    def test_unresolved_entry_must_use_in_class_notes(self):
        patch = {
            "schema_version": 1,
            "note": "COURSE101/Lectures/example/example.md",
            "entries": [student_entry(routing_status="unresolved")],
        }
        with self.assertRaisesRegex(PATCHES.PatchError, "must target"):
            PATCHES.validate_patch(patch)

    def test_teacher_block_keeps_asr_provenance(self):
        entry = {
            "id": "teacher-20260901-001",
            "actor": "teacher",
            "kind": "emphasis",
            "target_heading": "Core concept",
            "target_level": 2,
            "body": "The lecturer emphasized this distinction as assessment-relevant.",
            "source_anchor": "00:31:24",
            "confidence": "high",
            "routing_status": "matched",
        }
        modified, _ = PATCHES.apply_entries(NOTE, [entry])
        self.assertIn("[!important] Lecturer emphasis", modified)
        self.assertIn("ASR: 00:31:24", modified)


class FilesystemBackendTests(unittest.TestCase):
    def test_fs_roundtrip_inserts_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = "COURSE101/Lectures/example/example.md"
            destination = vault / note
            destination.parent.mkdir(parents=True)
            destination.write_text(NOTE, encoding="utf-8")
            original = PATCHES.read_note(note, vault, "fs")
            self.assertEqual(original, NOTE)
            modified, outcomes = PATCHES.apply_entries(original, [student_entry()])
            self.assertEqual(outcomes[0]["status"], "inserted")
            writer = PATCHES.write_note(note, original, modified, vault, "fs")
            self.assertEqual(writer, "filesystem-atomic")
            self.assertEqual(destination.read_text(encoding="utf-8"), modified)

    def test_fs_resolves_without_escaping_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            self.assertEqual(
                PATCHES.resolve_note_path("a/b.md", vault),
                (vault / "a" / "b.md").resolve(),
            )
        with self.assertRaisesRegex(PATCHES.PatchError, "escapes"):
            PATCHES.resolve_note_path("../outside.md", Path("/tmp"))

    def test_fs_read_reports_missing_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            with self.assertRaisesRegex(PATCHES.PatchError, "not found"):
                PATCHES.fs_read("missing.md", vault)


if __name__ == "__main__":
    unittest.main()
