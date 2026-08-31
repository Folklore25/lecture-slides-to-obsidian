import importlib.util
import hashlib
import re
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/build-canvas.py"
SPEC = importlib.util.spec_from_file_location("build_canvas", SCRIPT)
BUILD_CANVAS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILD_CANVAS)


def recall_model(with_asset: bool = False) -> dict:
    model = {
        "schema_version": 1,
        "profile": "lecture-notes",
        "mode": "pre-class",
        "title": "Synthetic lesson",
        "orientation": {
            "central_question": "How do the lesson's concepts produce the final outcome?",
            "one_sentence_answer": "Foundations enable a mechanism whose application works only inside a stated boundary.",
            "takeaways": [
                "Start from the prerequisite concept.",
                "Follow the mechanism rather than the slide order.",
                "Check the boundary before applying the result."
            ]
        },
        "groups": [
            {"id":"core-model","title":"Core model","summary":"The prerequisite and mechanism that drive the lesson.","order":1},
            {"id":"use-and-limits","title":"Use and limits","summary":"The result, application, and boundary conditions.","order":2}
        ],
        "concepts": [
            {"id":"prerequisite","group":"core-model","kind":"foundation","title":"Prerequisite","statement":"The initial concept supplies the terms needed to understand the mechanism.","details":["It defines the comparison baseline."],"recall_cue":"What must be known first?","source_heading":"Foundations","source_page":1},
            {"id":"mechanism","group":"core-model","kind":"mechanism","title":"Mechanism","statement":"The mechanism transforms the prerequisite into an observable intermediate result.","details":["Its steps must be read as a causal sequence."],"recall_cue":"What changes what?","source_heading":"Mechanism","source_page":2},
            {"id":"application","group":"use-and-limits","kind":"application","title":"Application","statement":"The application uses the mechanism to produce a practical decision or outcome.","details":["The result is useful only when assumptions hold."],"recall_cue":"When would this be used?","source_heading":"Application","source_page":3},
            {"id":"boundary","group":"use-and-limits","kind":"boundary","title":"Boundary","statement":"The boundary identifies the condition under which the application no longer follows.","details":["Crossing it changes the expected outcome."],"recall_cue":"When should the rule not be applied?","source_heading":"Limits","source_page":4}
        ],
        "relations": [
            {"from":"prerequisite","to":"mechanism","type":"enables","label":"provides the input model","why":"The mechanism uses terms defined by the prerequisite."},
            {"from":"mechanism","to":"application","type":"leads-to","label":"produces the usable outcome","why":"The application is the practical result of the mechanism."},
            {"from":"boundary","to":"application","type":"limits","label":"restricts when it applies","why":"The source states a condition where the application fails."}
        ],
        "coverage": [
            {"source_heading":"Foundations","source_page":1,"concepts":["prerequisite"]},
            {"source_heading":"Mechanism","source_page":2,"concepts":["mechanism"]},
            {"source_heading":"Application","source_page":3,"concepts":["application"]},
            {"source_heading":"Limits","source_page":4,"concepts":["boundary"]},
            {"source_heading":"In-class notes","source_page":4,"concepts":[],"omission_reason":"Empty in pre-class mode."}
        ],
        "synthesis": {
            "logic_chain":["Define the prerequisite.","Run the mechanism.","Apply the result only inside its boundary."],
            "distinctions":[{"terms":"Mechanism vs application","rule":"The mechanism explains change; the application uses that change for a purpose."}],
            "recall_prompts":["What is required before the mechanism?","How does the mechanism produce the result?","Which condition blocks the application?"],
            "in_class_additions":[]
        },
        "asset_links": []
    }
    if with_asset:
        model["asset_links"] = [
            {"concept":"mechanism","path":"assets/page-004-figure-01.png","caption":"Mechanism overview"}
        ]
    return model


class BuildCanvasTests(unittest.TestCase):
    def test_semantic_model_renders_stable_recall_map_and_vault_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            vault = Path(temp) / "vault"
            folder = vault / "COURSE101/Lectures/example-lesson"
            assets = folder / "assets"
            assets.mkdir(parents=True)
            note = folder / "example-lesson.md"
            note.write_text(
                "# Example lesson\n\n## Foundations\n\nText.\n\n## Mechanism\n\nText.\n\n"
                "## Application\n\nText.\n\n## Limits\n\nText.\n\n## In-class notes\n"
            )
            (assets / "page-004-figure-01.png").write_bytes(b"synthetic")
            model = recall_model(with_asset=True)
            first = BUILD_CANVAS.build_canvas(note, vault, "lecture-notes", model, assets)
            second = BUILD_CANVAS.build_canvas(note, vault, "lecture-notes", model, assets)
            self.assertEqual(first, second)
            file_nodes = [node for node in first["nodes"] if node["type"] == "file"]
            paths = {node["file"] for node in file_nodes}
            self.assertIn("COURSE101/Lectures/example-lesson/example-lesson.md", paths)
            self.assertIn(
                "COURSE101/Lectures/example-lesson/assets/page-004-figure-01.png",
                paths,
            )
            texts = [node.get("text", "") for node in first["nodes"]]
            self.assertTrue(any("# One-minute recall" in text for text in texts))
            self.assertEqual(sum("<!-- recall-map: concept -->" in text for text in texts), 4)
            self.assertTrue(all(edge.get("label") != "followed by" for edge in first["edges"]))
            all_ids = [item["id"] for item in first["nodes"] + first["edges"]]
            self.assertEqual(len(all_ids), len(set(all_ids)))
            self.assertTrue(all(re.fullmatch(r"[0-9a-f]{16}", value) for value in all_ids))

    def test_generic_outline_relation_is_rejected(self):
        model = recall_model()
        model["relations"][0]["label"] = "followed by"
        markdown = "\n".join(f"## {value}" for value in ["Foundations", "Mechanism", "Application", "Limits", "In-class notes"])
        with self.assertRaisesRegex(BUILD_CANVAS.CanvasBuildError, "structurally generic"):
            BUILD_CANVAS.validate_model(model, markdown, "lecture-notes")

    def test_render_metrics_replace_estimates_and_preserve_reflow(self):
        with tempfile.TemporaryDirectory() as temp:
            vault = Path(temp) / "vault"
            folder = vault / "COURSE101/Lectures/example-lesson"
            (folder / "assets").mkdir(parents=True)
            note = folder / "example-lesson.md"
            note.write_text(
                "# Example lesson\n\n## Foundations\n\nText.\n\n## Mechanism\n\nText.\n\n"
                "## Application\n\nText.\n\n## Limits\n\nText.\n\n## In-class notes\n"
            )
            first = BUILD_CANVAS.build_canvas(note, vault, "lecture-notes", recall_model())
            text_nodes = [node for node in first["nodes"] if node["type"] == "text"]
            metrics = {
                "schema_version": 1,
                "mode": "measure",
                "measurement_complete": True,
                "nodes": [
                    {
                        "id": node["id"],
                        "width": node["width"],
                        "required_height": node["height"] + 40,
                        "text_sha256": hashlib.sha256(node["text"].encode()).hexdigest(),
                    }
                    for node in text_nodes
                ],
            }
            second = BUILD_CANVAS.build_canvas(
                note, vault, "lecture-notes", recall_model(), render_metrics=metrics
            )
            first_by_id = {node["id"]: node for node in first["nodes"]}
            second_by_id = {node["id"]: node for node in second["nodes"]}
            for node in text_nodes:
                self.assertEqual(second_by_id[node["id"]]["height"], node["height"] + 40)
            first_synthesis_y = next(
                node["y"] for node in first["nodes"]
                if "<!-- recall-map: synthesis -->" in node.get("text", "")
            )
            second_synthesis_y = next(
                node["y"] for node in second["nodes"]
                if "<!-- recall-map: synthesis -->" in node.get("text", "")
            )
            self.assertGreater(second_synthesis_y, first_synthesis_y)
            self.assertEqual(set(first_by_id), set(second_by_id))

    def test_missing_section_coverage_is_rejected(self):
        model = recall_model()
        model["coverage"].pop()
        markdown = "\n".join(f"## {value}" for value in ["Foundations", "Mechanism", "Application", "Limits", "In-class notes"])
        with self.assertRaisesRegex(BUILD_CANVAS.CanvasBuildError, "coverage is missing"):
            BUILD_CANVAS.validate_model(model, markdown, "lecture-notes")

    def test_heading_page_mismatch_is_rejected(self):
        model = recall_model()
        model["concepts"][0]["source_page"] = 2
        markdown = (
            "---\nsource_pages: 4\n---\n<!-- source-page: 1 -->\n## Foundations\n"
            "<!-- source-page: 2 -->\n## Mechanism\n<!-- source-page: 3 -->\n## Application\n"
            "<!-- source-page: 4 -->\n## Limits\n## In-class notes\n"
        )
        with self.assertRaisesRegex(BUILD_CANVAS.CanvasBuildError, "heading/page pair"):
            BUILD_CANVAS.validate_model(model, markdown, "lecture-notes")

    def test_pre_class_model_cannot_claim_class_additions(self):
        model = recall_model()
        model["synthesis"]["in_class_additions"] = ["The lecturer emphasized a likely exam topic."]
        markdown = "\n".join(f"## {value}" for value in ["Foundations", "Mechanism", "Application", "Limits", "In-class notes"])
        with self.assertRaisesRegex(BUILD_CANVAS.CanvasBuildError, "pre-class"):
            BUILD_CANVAS.validate_model(model, markdown, "lecture-notes")

    def test_note_outside_vault_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            vault = base / "vault"
            vault.mkdir()
            note = base / "outside.md"
            note.write_text("# Outside\n")
            with self.assertRaises(BUILD_CANVAS.CanvasBuildError):
                BUILD_CANVAS.build_canvas(note, vault, "lecture-notes", recall_model())


if __name__ == "__main__":
    unittest.main()
