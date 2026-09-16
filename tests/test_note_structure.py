import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills/lecture-slides-to-obsidian"
PLANNER = SKILL / "scripts/plan-note-structure.py"
VALIDATOR = SKILL / "scripts/validate-output.py"
CANVAS_SKILL = REPO / "skills/obsidian-canvas-designer"

PAGE_GROUPS = REPO / "tests/fixtures/staging/page-groups.json"
PLAN = REPO / "tests/fixtures/staging/note-plan.json"
LEDGER = REPO / "tests/fixtures/staging/page-ledger.json"
SYNTHESIS_FOLDER = REPO / "tests/fixtures/synthetic/section-notes-folder"
REPORT = REPO / "tests/fixtures/staging/conversion-report.md"


def run_script(script, arguments):
    result = subprocess.run(
        [sys.executable, str(script), *map(str, arguments)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


def run_validator(folder, extra=()):
    result = subprocess.run(
        [
            sys.executable, str(VALIDATOR), str(folder),
            "--fixture-mode", "--report", str(REPORT), *map(str, extra),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, json.loads(result.stdout)


def planner_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("note_plan", PLANNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NoteStructureTests(unittest.TestCase):
    def test_planner_drafts_a_plan_and_a_ledger_from_source_outline(self):
        with tempfile.TemporaryDirectory() as temp:
            plan_path = Path(temp) / "note-plan.json"
            ledger_path = Path(temp) / "page-ledger.json"
            code, output = run_script(PLANNER, [
                "--page-groups", PAGE_GROUPS,
                "--profile", "lecture-notes",
                "--granularity", "single-note",
                "--slug", "week3-qualitative-research",
                "--title", "Week 3 Qualitative Research",
                "--output", plan_path,
                "--ledger-output", ledger_path,
            ])
            self.assertEqual(code, 0, output)
            plan = json.loads(plan_path.read_text())
            ledger = json.loads(ledger_path.read_text())
            self.assertTrue(plan["draft"])
            self.assertEqual(plan["source_pages"], 7)
            self.assertEqual(len(plan["notes"]), 1)
            self.assertTrue(all(item["disposition"] in {"kept", "merged", "dropped"} for item in ledger["pages"]))
            self.assertEqual(len(ledger["pages"]), 7)

    def test_planner_refuses_to_plan_other_profiles(self):
        code, output = run_script(PLANNER, [
            "--page-groups", PAGE_GROUPS,
            "--profile", "policy-document",
            "--granularity", "single-note",
            "--slug", "example-policy",
            "--title", "Example Policy",
            "--output", "/tmp/unused-plan.json",
            "--ledger-output", "/tmp/unused-ledger.json",
        ])
        self.assertNotEqual(code, 0)
        self.assertIn("reconstruct-note.py", output)

    def test_section_notes_granularity_creates_one_note_per_section(self):
        planner = planner_module()

        def title(text, level=2):
            return {"type": "title", "content": {"title_content": [{"type": "text", "content": text}], "level": level}}

        def paragraph(text):
            return {"type": "paragraph", "content": {"paragraph_content": [{"type": "text", "content": text}]}}

        pages = [
            [title("Week 3 Qualitative Research", 1)],
            [paragraph("1. Grounded theory\n2. Action research\n3. Ethnography")],
            [title("1. Grounded theory"), paragraph("Theory built from data.")],
            [title("2. Action research"), paragraph("Plan, act, observe, reflect.")],
            [title("3. Ethnography"), paragraph("Studying a culture in the field.")],
        ]
        plan, ledger = planner.build_plan(
            pages, "lecture-notes", "section-notes", "week3", "Week 3"
        )
        self.assertEqual(len(plan["notes"]), 3)
        self.assertEqual(
            [note["title"] for note in plan["notes"]],
            ["1. Grounded theory", "2. Action research", "3. Ethnography"],
        )
        self.assertEqual(len(ledger["pages"]), 5)
        self.assertNotEqual(planner.recommend_granularity(2, 40), "section-notes")
        self.assertEqual(planner.recommend_granularity(4, 120), "section-notes")

    def section_pages(self):
        def title(text, level=2):
            return {"type": "title", "content": {"title_content": [{"type": "text", "content": text}], "level": level}}

        def paragraph(text):
            return {"type": "paragraph", "content": {"paragraph_content": [{"type": "text", "content": text}]}}

        return [
            [title("Lecture 4 - Feature Engineering", 1)],
            [paragraph("1. Introduction\\n2. Quick review\\n3. Feature importance\\n4. Selection and reduction")],
            [title("1. Introduction"), paragraph("Feature engineering turns raw columns into representations a model can use, and it decides most of the achievable accuracy before any algorithm is chosen.")],
            [title("2. Quick review"), paragraph("The previous lecture covered linear regression, least squares, and the interpretation of coefficients in a model with a single explanatory variable.")],
            [title("3. Feature importance"), paragraph("Importance ranks how much each feature contributes to a fitted model, and the ranking depends on whether it is measured by impurity, by coefficient size, or by permutation.")],
            [title("4. Selection and reduction"), paragraph("Selection keeps a subset of the original columns while reduction projects them into fewer dimensions, and the two families are chosen by whether interpretability matters.")],
        ]

    def test_section_note_slugs_carry_a_source_order_ordinal(self):
        planner = planner_module()
        plan, _ = planner.build_plan(
            self.section_pages(), "lecture-notes", "section-notes",
            "l04-feature-engineering", "Lecture 4",
        )
        slugs = [note["slug"] for note in plan["notes"]]
        self.assertEqual(slugs, [
            "l04-feature-engineering-01-introduction",
            "l04-feature-engineering-02-quick-review",
            "l04-feature-engineering-03-feature-importance",
            "l04-feature-engineering-04-selection-and-reduction",
        ])
        # A plain filename sort now matches the order of the source document.
        self.assertEqual(slugs, sorted(slugs))

    def test_section_slug_strips_the_headings_own_numbering(self):
        planner = planner_module()
        self.assertEqual(
            planner.section_note_slug("doc", 0, "1. Introduction"), "doc-01-introduction"
        )
        self.assertEqual(
            planner.section_note_slug("doc", 2, "A. Interviews"), "doc-03-interviews"
        )

    def test_non_latin_heading_gets_a_readable_fallback(self):
        planner = planner_module()
        self.assertEqual(
            planner.section_note_slug("doc", 0, "第一节 指数的概念"), "doc-01-section"
        )

    def test_a_heading_starting_with_c_keeps_its_first_letter(self):
        # The list-marker alternative must not eat the leading letter of a real word.
        planner = planner_module()
        self.assertEqual(planner.section_note_slug("doc", 0, "Content"), "doc-01-content")
        self.assertEqual(
            planner.section_note_slug("doc", 1, "Case studies"), "doc-02-case-studies"
        )

    def test_section_note_without_an_ordinal_is_rejected(self):
        planner = planner_module()
        pages = self.section_pages()
        plan, _ = planner.build_plan(
            pages, "lecture-notes", "section-notes", "doc", "Doc"
        )
        plan["draft"] = False
        plan["notes"][0]["slug"] = "doc-introduction"
        errors = planner.validate_plan(plan)
        self.assertTrue(any("two-digit source-order ordinal" in item for item in errors))

    def test_non_contiguous_section_ordinals_are_rejected(self):
        planner = planner_module()
        plan, _ = planner.build_plan(
            self.section_pages(), "lecture-notes", "section-notes", "doc", "Doc"
        )
        plan["draft"] = False
        plan["notes"][1]["slug"] = "doc-07-quick-review"
        errors = planner.validate_plan(plan)
        self.assertTrue(any("ordinals must be 01.." in item for item in errors))

    def test_section_notes_must_stay_in_source_page_order(self):
        planner = planner_module()
        plan, _ = planner.build_plan(
            self.section_pages(), "lecture-notes", "section-notes", "doc", "Doc"
        )
        plan["draft"] = False
        plan["notes"].reverse()
        errors = planner.validate_plan(plan)
        self.assertTrue(any("source page order" in item for item in errors))

    def test_repeated_template_chrome_is_detected_and_dropped(self):
        planner = planner_module()

        def visual(x0, y0, x1, y1):
            return {"type": "image", "bbox": [x0, y0, x1, y1], "content": {"image_caption": []}}

        def title(text):
            return {"type": "title", "content": {"title_content": [{"type": "text", "content": text}], "level": 2}}

        def paragraph(text):
            return {"type": "paragraph", "content": {"paragraph_content": [{"type": "text", "content": text}]}}

        logo = visual(10, 10, 120, 60)
        pages = [
            [title("Week 3"), logo],
            [title("Methodology"), paragraph("A strategy of inquiry. 1. Grounded theory 2. Action research"), logo],
            [title("Grounded theory"), paragraph("Open coding. Axial coding."), logo],
            [title("Action research"), paragraph("Plan, act, observe, reflect."), logo, visual(100, 150, 600, 400)],
            [title("Ethnography"), paragraph("Studying a culture in the field."), logo],
            [title("Case studies"), paragraph("Holistic analysis of one instance."), logo],
        ]
        plan, ledger = planner.build_plan(pages, "lecture-notes", "single-note", "week3", "Week 3")
        self.assertEqual(ledger["detected_repeated_chrome"], 1)
        by_page = {item["page"]: item for item in ledger["pages"]}
        for page in (2, 3, 4, 5, 6):
            visuals = by_page[page].get("visuals", [])
            self.assertIn({"disposition": "dropped", "reason": "repeated-chrome"}, visuals)
        # The one real diagram on page 4 survives as a kept visual awaiting a name.
        kept = [v for v in by_page[4]["visuals"] if v["disposition"] == "kept"]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["asset"], "")

    def test_a_unique_visual_on_every_page_is_not_called_chrome(self):
        planner = planner_module()

        def visual(index):
            return {"type": "image", "bbox": [0, 0, 100 + index * 10, 200], "content": {"image_caption": []}}

        pages = [[visual(index)] for index in range(6)]
        signals = [planner.page_signals(index, page) for index, page in enumerate(pages)]
        self.assertEqual(planner.chrome_signatures(signals), set())

    def test_chrome_needs_a_minimum_number_of_pages(self):
        planner = planner_module()

        def visual():
            return {"type": "image", "bbox": [10, 10, 120, 60], "content": {"image_caption": []}}

        pages = [[visual()] for _ in range(3)]
        signals = [planner.page_signals(index, page) for index, page in enumerate(pages)]
        self.assertEqual(len(planner.chrome_signatures(signals)), 1)
        self.assertEqual(planner.chrome_signatures(signals[:2]), set())

    def test_draft_plan_is_rejected_until_reviewed(self):
        planner = planner_module()
        plan = json.loads(PLAN.read_text())
        plan["draft"] = True
        errors = planner.validate_plan(plan)
        self.assertTrue(any("still a draft" in item for item in errors))

    def test_slide_furniture_heading_is_rejected(self):
        planner = planner_module()
        plan = json.loads(PLAN.read_text())
        plan["notes"][0]["sections"][0]["heading"] = "Slide 2"
        errors = planner.validate_plan(plan)
        self.assertTrue(any("slide furniture" in item for item in errors))

    def test_duplicate_section_heading_is_rejected(self):
        planner = planner_module()
        plan = json.loads(PLAN.read_text())
        sections = plan["notes"][0]["sections"]
        sections[1]["heading"] = sections[0]["heading"]
        errors = planner.validate_plan(plan)
        self.assertTrue(any("duplicates another section" in item for item in errors))

    def test_ledger_must_account_for_every_source_page(self):
        planner = planner_module()
        plan = json.loads(PLAN.read_text())
        ledger = json.loads(LEDGER.read_text())
        ledger["pages"] = ledger["pages"][:-1]
        errors = planner.validate_ledger(ledger, plan, False)
        self.assertTrue(any("missing source pages" in item for item in errors))

    def test_ledger_drop_requires_a_supported_reason(self):
        planner = planner_module()
        plan = json.loads(PLAN.read_text())
        ledger = json.loads(LEDGER.read_text())
        ledger["pages"][0]["reason"] = "looked boring"
        errors = planner.validate_ledger(ledger, plan, False)
        self.assertTrue(any("supported reason" in item for item in errors))

    def test_ledger_rejects_unknown_section(self):
        planner = planner_module()
        plan = json.loads(PLAN.read_text())
        ledger = json.loads(LEDGER.read_text())
        ledger["pages"][1]["section"] = "9. Invented section"
        errors = planner.validate_ledger(ledger, plan, False)
        self.assertTrue(any("unknown section" in item for item in errors))

    def image_only_plan_and_ledger(self):
        planner = planner_module()

        def title(text, level=2):
            return {"type": "title", "content": {"title_content": [{"type": "text", "content": text}], "level": level}}

        def para(text):
            return {"type": "paragraph", "content": {"paragraph_content": [{"type": "text", "content": text}]}}

        def figure(bbox):
            return {"type": "image", "bbox": bbox, "content": {"image_caption": [{"type": "text", "content": "PCA"}]}}

        pages = [
            [title("Lecture 4", 1), para("A reasonably long opening paragraph that is well over the divider threshold so this page reads as prose content rather than a title slide in the heuristic.")],
            [title("PCA"), figure([100, 150, 800, 600])],
        ]
        plan, _ = planner.build_plan(pages, "lecture-notes", "single-note", "l04", "Lecture 4")
        plan["draft"] = False
        ledger = {
            "schema_version": 1, "draft": False, "source_pages": 2,
            "pages": [
                {"page": 1, "disposition": "kept", "note": "l04", "section": "Lecture 4",
                 "evidence": "A reasonably long opening paragraph", "visuals": []},
                {"page": 2, "disposition": "dropped", "reason": "non-substantive"},
            ],
        }
        return planner, plan, ledger

    def test_a_visual_page_cannot_be_dropped_as_non_substantive(self):
        planner, plan, ledger = self.image_only_plan_and_ledger()
        self.assertEqual(plan["_signals"]["image_only_pages"], [2])
        errors = planner.validate_ledger(ledger, plan, False)
        self.assertTrue(any("carries 1 detected visual" in item for item in errors))

    def test_a_visual_page_may_be_dropped_for_a_visual_aware_reason(self):
        planner, plan, ledger = self.image_only_plan_and_ledger()
        ledger["pages"][1]["reason"] = "duplicate"
        errors = planner.validate_ledger(ledger, plan, False)
        self.assertEqual([e for e in errors if "carries" in e], [])

    def test_a_furniture_page_without_visuals_can_still_be_non_substantive(self):
        planner, plan, ledger = self.image_only_plan_and_ledger()
        ledger["pages"][1] = {"page": 2, "disposition": "dropped", "reason": "non-substantive"}
        plan["_signals"]["page_signals"][1]["visual_count"] = 0
        errors = planner.validate_ledger(ledger, plan, False)
        self.assertEqual([e for e in errors if "carries" in e], [])

    def test_kept_page_must_declare_its_visuals(self):
        planner = planner_module()
        plan = json.loads(PLAN.read_text())
        ledger = json.loads(LEDGER.read_text())
        del ledger["pages"][1]["visuals"]
        errors = planner.validate_ledger(ledger, plan, False)
        self.assertTrue(any("must declare visuals" in item for item in errors))

    def test_kept_visual_must_name_an_asset(self):
        planner = planner_module()
        plan = json.loads(PLAN.read_text())
        ledger = json.loads(LEDGER.read_text())
        ledger["pages"][1]["visuals"] = [{"disposition": "kept", "asset": ""}]
        errors = planner.validate_ledger(ledger, plan, False)
        self.assertTrue(any("names no asset" in item for item in errors))

    def test_dropped_visual_needs_a_controlled_reason(self):
        planner = planner_module()
        plan = json.loads(PLAN.read_text())
        ledger = json.loads(LEDGER.read_text())
        ledger["pages"][5]["visuals"] = [{"disposition": "dropped", "reason": "did not feel useful"}]
        errors = planner.validate_ledger(ledger, plan, False)
        self.assertTrue(any("dropped without a supported reason" in item for item in errors))

    def test_superseded_by_table_must_name_the_replacement(self):
        planner = planner_module()
        plan = json.loads(PLAN.read_text())
        ledger = json.loads(LEDGER.read_text())
        ledger["pages"][5]["visuals"] = [{"disposition": "dropped", "reason": "superseded-by-table"}]
        errors = planner.validate_ledger(ledger, plan, False)
        self.assertTrue(any("rendered_as" in item for item in errors))

    def test_ledger_heavy_drop_requires_explicit_approval(self):
        planner = planner_module()
        plan = json.loads(PLAN.read_text())
        ledger = json.loads(LEDGER.read_text())
        for item in ledger["pages"][:5]:
            item.clear()
            item.update({"page": ledger["pages"].index(item) + 1, "disposition": "dropped", "reason": "page-furniture"})
        self.assertTrue(any("drops" in item for item in planner.validate_ledger(ledger, plan, False)))
        self.assertEqual(planner.validate_ledger(ledger, plan, True), [])


class SynthesisValidationTests(unittest.TestCase):
    def test_content_driven_fixture_passes_every_gate(self):
        code, result = run_validator(SYNTHESIS_FOLDER, [
            "--plan", PLAN, "--ledger", LEDGER, "--page-groups", PAGE_GROUPS,
        ])
        self.assertEqual(code, 0, result["errors"])
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["content_conservation"]), 6)
        self.assertTrue(all(row["recall"] >= 0.35 for row in result["content_conservation"]))

    def test_page_markers_are_rejected_in_content_driven_notes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(SYNTHESIS_FOLDER, folder)
            note = folder / "week3-qualitative-research.md"
            note.write_text(
                note.read_text().replace(
                    "## 1. Research methodology and the qualitative distinction",
                    "<!-- source-page: 1 -->\n\n## 1. Research methodology and the qualitative distinction",
                )
            )
            code, result = run_validator(folder, [
                "--plan", PLAN, "--ledger", LEDGER, "--page-groups", PAGE_GROUPS,
            ])
            self.assertNotEqual(code, 0)
            self.assertTrue(any("page markers are not part" in item for item in result["errors"]))

    def test_plan_and_ledger_are_required_for_content_driven_notes(self):
        code, result = run_validator(SYNTHESIS_FOLDER)
        self.assertNotEqual(code, 0)
        self.assertTrue(any("--plan and --ledger" in item for item in result["errors"]))

    def test_note_outside_the_plan_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(SYNTHESIS_FOLDER, folder)
            (folder / "extra-note.md").write_text((folder / "week3-qualitative-research.md").read_text())
            code, result = run_validator(folder, [
                "--plan", PLAN, "--ledger", LEDGER, "--page-groups", PAGE_GROUPS,
            ])
            self.assertNotEqual(code, 0)
            self.assertTrue(
                any("outside the note plan" in item or "one Canvas per note" in item for item in result["errors"])
            )

    def test_missing_planned_section_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(SYNTHESIS_FOLDER, folder)
            note = folder / "week3-qualitative-research.md"
            note.write_text(note.read_text().replace("## 3. Action research", "## 3. Something else"))
            code, result = run_validator(folder, [
                "--plan", PLAN, "--ledger", LEDGER, "--page-groups", PAGE_GROUPS,
            ])
            self.assertNotEqual(code, 0)
            self.assertTrue(any("outside the finalized note plan" in item for item in result["errors"]))

    def test_silent_page_loss_is_rejected_by_conservation(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(SYNTHESIS_FOLDER, folder)
            note = folder / "week3-qualitative-research.md"
            text = note.read_text()
            start = text.index("## 2. Grounded theory")
            end = text.index("## 3. Action research")
            note.write_text(text[:start] + "## 2. Grounded theory\n\nA short placeholder sentence about theory.\n\n" + text[end:])
            code, result = run_validator(folder, [
                "--plan", PLAN, "--ledger", LEDGER, "--page-groups", PAGE_GROUPS,
            ])
            self.assertNotEqual(code, 0)
            self.assertTrue(any("not represented" in item for item in result["errors"]))

    def test_declared_recall_exemption_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            staging = Path(temp) / "staging"
            staging.mkdir()
            shutil.copytree(SYNTHESIS_FOLDER, folder)
            note = folder / "week3-qualitative-research.md"
            text = note.read_text()
            start = text.index("## 2. Grounded theory")
            end = text.index("## 3. Action research")
            note.write_text(text[:start] + "## 2. Grounded theory\n\nA short placeholder sentence about theory.\n\n" + text[end:])
            ledger = json.loads(LEDGER.read_text())
            for item in ledger["pages"]:
                if item.get("page") == 3:
                    item["recall_exempt"] = True
                    item["recall_exempt_reason"] = "Synthetic fixture: page deliberately condensed."
                    item["evidence"] = "A short placeholder sentence about theory"
            ledger_path = staging / "page-ledger.json"
            ledger_path.write_text(json.dumps(ledger))
            code, result = run_validator(folder, [
                "--plan", PLAN, "--ledger", ledger_path, "--page-groups", PAGE_GROUPS,
            ])
            self.assertEqual(code, 0, result["errors"])

    def test_page_number_asset_prefix_is_rejected_for_content_driven_notes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(SYNTHESIS_FOLDER, folder)
            (folder / "assets/page-004-figure-01.png").write_bytes(b"synthetic")
            code, result = run_validator(folder, [
                "--plan", PLAN, "--ledger", LEDGER, "--page-groups", PAGE_GROUPS,
            ])
            self.assertNotEqual(code, 0)
            self.assertTrue(any("page-number prefix" in item for item in result["errors"]))

    def test_kept_visual_missing_from_assets_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            staging = Path(temp) / "staging"
            staging.mkdir()
            shutil.copytree(SYNTHESIS_FOLDER, folder)
            ledger = json.loads(LEDGER.read_text())
            ledger["pages"][1]["visuals"] = [{"disposition": "kept", "asset": "never-extracted.png"}]
            ledger_path = staging / "page-ledger.json"
            ledger_path.write_text(json.dumps(ledger))
            code, result = run_validator(folder, [
                "--plan", PLAN, "--ledger", ledger_path, "--page-groups", PAGE_GROUPS,
            ])
            self.assertNotEqual(code, 0)
            self.assertTrue(any("missing from assets/" in item for item in result["errors"]))

    def test_asset_not_declared_in_the_ledger_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            staging = Path(temp) / "staging"
            staging.mkdir()
            shutil.copytree(SYNTHESIS_FOLDER, folder)
            note = folder / "week3-qualitative-research.md"
            note.write_text(
                note.read_text().replace(
                    "![[assets/qualitative-research-cycle.png|420]]",
                    "![[assets/qualitative-research-cycle.png|420]]\n\n![[assets/undeclared-extra.png|300]]",
                )
            )
            (folder / "assets/undeclared-extra.png").write_bytes(b"synthetic")
            code, result = run_validator(folder, [
                "--plan", PLAN, "--ledger", LEDGER, "--page-groups", PAGE_GROUPS,
            ])
            self.assertNotEqual(code, 0)
            self.assertTrue(
                any("not declared as kept in the page ledger" in item for item in result["errors"])
            )

    def test_unreferenced_content_driven_asset_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(SYNTHESIS_FOLDER, folder)
            (folder / "assets/orphan-diagram.png").write_bytes(b"synthetic")
            code, result = run_validator(folder, [
                "--plan", PLAN, "--ledger", LEDGER, "--page-groups", PAGE_GROUPS,
            ])
            self.assertNotEqual(code, 0)
            self.assertTrue(
                any("not declared as kept in the page ledger" in item for item in result["errors"])
            )

    def test_qa_state_is_deleted_on_success(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            staging = Path(temp) / "staging"
            staging.mkdir()
            shutil.copytree(SYNTHESIS_FOLDER, folder)
            report = staging / "conversion-report.md"
            plan = staging / "note-plan.json"
            ledger = staging / "page-ledger.json"
            page_groups = staging / "page-groups.json"
            shutil.copy2(REPORT, report)
            shutil.copy2(PLAN, plan)
            shutil.copy2(LEDGER, ledger)
            shutil.copy2(PAGE_GROUPS, page_groups)
            result = subprocess.run(
                [
                    sys.executable, str(VALIDATOR), str(folder),
                    "--fixture-mode", "--report", str(report),
                    "--plan", str(plan), "--ledger", str(ledger),
                    "--page-groups", str(page_groups),
                    "--delete-qa-on-success",
                ],
                capture_output=True, text=True, check=False,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0, payload["errors"])
            self.assertTrue(payload["note_plan_deleted"])
            self.assertTrue(payload["page_ledger_deleted"])
            for path in (report, plan, ledger, page_groups):
                self.assertFalse(path.exists())


class RecallSkeletonContractTests(unittest.TestCase):
    def skeleton_module(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "recall_skeleton", CANVAS_SKILL / "scripts/recall-skeleton.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_note_without_page_markers_reports_no_page_provenance(self):
        skeleton = self.skeleton_module()
        text = (
            "---\nconversion_profile: lecture-notes\n---\n# Week 3\n\n"
            "## Foundations\n\nBody.\n\n## Methods\n\nBody.\n"
        )
        inspection = skeleton.inspect_note(text)
        self.assertEqual(inspection["hard_errors"], [])
        self.assertEqual(inspection["page_provenance"], "none")
        self.assertEqual(
            [(item["heading"], item["source_page"]) for item in inspection["h2_sections"]],
            [("Foundations", None), ("Methods", None)],
        )
        draft = skeleton.create_skeleton(inspection, "lecture-notes", "pre-class")
        self.assertEqual(len(draft["coverage"]), 2)
        self.assertTrue(all(row["source_page"] is None for row in draft["coverage"]))

    def test_marker_note_still_requires_page_provenance(self):
        skeleton = self.skeleton_module()
        text = (
            "---\nsource_pages: 2\n---\n# Week 3\n\n## Foundations\n\nBody.\n\n"
            "<!-- source-page: 1 -->\n\n## Later\n\nBody.\n"
        )
        inspection = skeleton.inspect_note(text)
        self.assertEqual(inspection["page_provenance"], "markers")
        self.assertTrue(any("without a preceding source-page marker" in item for item in inspection["hard_errors"]))

    def test_duplicate_content_headings_are_reported_without_pages(self):
        skeleton = self.skeleton_module()
        text = "# Week 3\n\n## Repeated\n\nBody.\n\n## Repeated\n\nMore.\n"
        inspection = skeleton.inspect_note(text)
        self.assertTrue(any("Duplicate H2" in item for item in inspection["hard_errors"]))


if __name__ == "__main__":
    unittest.main()
