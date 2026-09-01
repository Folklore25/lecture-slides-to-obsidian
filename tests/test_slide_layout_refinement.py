import importlib.util
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/slide-layout-refiner/scripts/validate-layout-refinement.py"
SPEC = importlib.util.spec_from_file_location("validate_layout_refinement", SCRIPT)
REFINER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(REFINER)


BASE = """---
type: course-material
source_pages: 2
---
# Example deck

<!-- source-page: 1 -->

## Slide title

▶ First point

## Systematic

- about research design

![[assets/page-001-figure-01.png]]

<!-- source-page: 2 -->

## Second slide

Final text.
"""


CANDIDATE = """---
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
        result = REFINER.validate_refinement(BASE, CANDIDATE)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["page_markers"], [1, 2])
        self.assertEqual(result["candidate_bullet_glyphs"], 0)
        page_one = next(page for page in result["pages"] if page["page"] == 1)
        self.assertEqual(page_one["base_h2"], 2)
        self.assertEqual(page_one["candidate_h2"], 1)

    def test_visible_text_change_is_rejected(self):
        changed = CANDIDATE.replace("First point", "Changed point")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("visible text tokens" in item for item in result["errors"]))

    def test_text_reordering_is_rejected(self):
        changed = CANDIDATE.replace("- First point\n\n### Systematic", "### Systematic\n\n- First point")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])

    def test_asset_cannot_cross_slide_marker(self):
        changed = CANDIDATE.replace(
            "> ![[assets/page-001-figure-01.png|480]]\n\n<!-- source-page: 2 -->",
            "<!-- source-page: 2 -->\n\n![[assets/page-001-figure-01.png|480]]",
        )
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("asset set" in item for item in result["errors"]))

    def test_marker_line_change_is_rejected(self):
        changed = CANDIDATE.replace("<!-- source-page: 1 -->", "<!--  source-page: 1  -->")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("source-page markers" in item for item in result["errors"]))

    def test_frontmatter_change_is_rejected(self):
        changed = CANDIDATE.replace("source_pages: 2", "source_pages: 3")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertIn("frontmatter changed", result["errors"])

    def test_multiple_h2_titles_in_one_slide_are_rejected(self):
        changed = CANDIDATE.replace("### Systematic", "## Systematic")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("more than one H2" in item for item in result["errors"]))

    def test_h4_without_h3_region_is_rejected(self):
        changed = CANDIDATE.replace("### Systematic", "#### Systematic")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("H4 appears" in item for item in result["errors"]))

    def test_callout_layout_is_rejected(self):
        changed = CANDIDATE.replace("- First point", "> [!note]\n> First point")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("callout syntax" in item for item in result["errors"]))

    def test_raw_html_layout_is_rejected(self):
        changed = CANDIDATE.replace("Final text.", "<div>Final text.</div>")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("raw HTML" in item for item in result["errors"]))

    def test_new_horizontal_rule_is_rejected(self):
        changed = CANDIDATE.replace("### Systematic", "---\n\n### Systematic")
        result = REFINER.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("horizontal rule" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
