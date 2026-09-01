import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/slide-layout-refiner/scripts/validate-layout-refinement.py"
SPEC = importlib.util.spec_from_file_location("validate_layout_refinement", SCRIPT)
REFINER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(REFINER)


BASE = r"""---
type: course-material
source_pages: 2
---
# Example deck

<!-- source-page: 1 -->

## Slide title

▶ First point

## Systematic

\- about research design

![[assets/page-001-figure-01.png]]

<!-- source-page: 2 -->

## Second slide

Final text.
"""


REFINED = """---
type: course-material
source_pages: 2
---
# Example deck

<!-- source-page: 1 -->

## Slide title

- First point

### Systematic

	- about research design

> ![[assets/page-001-figure-01.png|480]]

<!-- source-page: 2 -->

## Second slide

Final text.
"""


class SlideLayoutRefinementTests(unittest.TestCase):
    def test_page_local_layout_changes_preserve_content(self):
        result = REFINER.validate_refinement(BASE, REFINED)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["page_markers"], [1, 2])
        self.assertEqual(result["refined_bullet_glyphs"], 0)
        self.assertEqual(result["refined_escaped_list_markers"], 0)
        page_one = next(page for page in result["pages"] if page["page"] == 1)
        self.assertEqual(page_one["snapshot_h2"], 2)
        self.assertEqual(page_one["refined_h2"], 1)

    def test_visible_text_change_is_rejected(self):
        changed = REFINED.replace("First point", "Changed point")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("visible text tokens" in item for item in result["errors"]))

    def test_text_reordering_is_rejected(self):
        changed = REFINED.replace("- First point\n\n### Systematic", "### Systematic\n\n- First point")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])

    def test_asset_cannot_cross_slide_marker(self):
        changed = REFINED.replace(
            "> ![[assets/page-001-figure-01.png|480]]\n\n<!-- source-page: 2 -->",
            "<!-- source-page: 2 -->\n\n![[assets/page-001-figure-01.png|480]]",
        )
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("asset set" in item for item in result["errors"]))

    def test_marker_line_change_is_rejected(self):
        changed = REFINED.replace("<!-- source-page: 1 -->", "<!--  source-page: 1  -->")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("source-page markers" in item for item in result["errors"]))

    def test_frontmatter_change_is_rejected(self):
        changed = REFINED.replace("source_pages: 2", "source_pages: 3")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertIn("frontmatter changed", result["errors"])

    def test_multiple_h2_titles_in_one_slide_are_rejected(self):
        changed = REFINED.replace("### Systematic", "## Systematic")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("more than one H2" in item for item in result["errors"]))

    def test_h4_without_h3_region_is_rejected(self):
        changed = REFINED.replace("### Systematic", "#### Systematic")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("H4 appears" in item for item in result["errors"]))

    def test_callout_layout_is_rejected(self):
        changed = REFINED.replace("- First point", "> [!note]\n> First point")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("callout syntax" in item for item in result["errors"]))

    def test_raw_html_layout_is_rejected(self):
        changed = REFINED.replace("Final text.", "<div>Final text.</div>")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("raw HTML" in item for item in result["errors"]))

    def test_new_horizontal_rule_is_rejected(self):
        changed = REFINED.replace("### Systematic", "---\n\n### Systematic")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("horizontal rule" in item for item in result["errors"]))

    def test_escaped_list_marker_must_be_normalized(self):
        changed = REFINED.replace("\t- about research design", "\t\\- about research design")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("escaped list marker remains" in item for item in result["errors"]))

    def test_cli_validates_direct_overwrite_without_second_vault_note(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            run = root / "tmp/run-1"
            target = vault / "COURSE101/example.md"
            snapshot = run / "before.md"
            report = run / "layout-refinement-report.json"
            target.parent.mkdir(parents=True)
            run.mkdir(parents=True)
            snapshot.write_text(BASE)
            target.write_text(REFINED)
            result = subprocess.run(
                [str(SCRIPT), "--snapshot", str(snapshot), "--target", str(target),
                 "--vault-root", str(vault), "--report", str(report)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(result.stdout)
            self.assertFalse(data["restored"])
            self.assertEqual(target.read_text(), REFINED)
            self.assertEqual(list(target.parent.glob("*.md")), [target])
            self.assertTrue(report.is_file())

    def test_cli_rolls_back_invalid_overwrite_without_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            run = root / "tmp/run-2"
            target = vault / "COURSE101/example.md"
            snapshot = run / "before.md"
            report = run / "layout-refinement-report.json"
            target.parent.mkdir(parents=True)
            run.mkdir(parents=True)
            snapshot.write_text(BASE)
            target.write_text(REFINED.replace("First point", "Changed point"))
            result = subprocess.run(
                [str(SCRIPT), "--snapshot", str(snapshot), "--target", str(target),
                 "--vault-root", str(vault), "--report", str(report)],
                text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertTrue(data["restored"])
            self.assertEqual(target.read_text(), BASE)

    def test_cli_rejects_snapshot_inside_vault(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            target = vault / "COURSE101/example.md"
            snapshot = vault / "temporary/before.md"
            report = root / "tmp/layout-refinement-report.json"
            target.parent.mkdir(parents=True)
            snapshot.parent.mkdir(parents=True)
            report.parent.mkdir(parents=True)
            snapshot.write_text(BASE)
            target.write_text(REFINED)
            result = subprocess.run(
                [str(SCRIPT), "--snapshot", str(snapshot), "--target", str(target),
                 "--vault-root", str(vault), "--report", str(report)],
                text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside the Obsidian vault", result.stdout)


if __name__ == "__main__":
    unittest.main()
