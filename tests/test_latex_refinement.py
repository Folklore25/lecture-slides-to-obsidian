import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "skills/obsidian-latex-refiner/scripts"
VALIDATOR_SCRIPT = SCRIPTS / "validate-latex-refinement.py"
NORMALIZER_SCRIPT = SCRIPTS / "normalize-latex.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("latex_validator_under_test", VALIDATOR_SCRIPT)
NORMALIZER = load_module("latex_normalizer_under_test", NORMALIZER_SCRIPT)


BASE = r"""---
type: course-material
source_pages: 2
---

# Example deck

<!-- source-page: 1 -->

## Energy

Einstein wrote \(E = mc^2\).

\[
\begin{align}
E &= mc^2\label{eq:energy} \\
p &= mv\nonumber
\end{align}
\]

![[assets/page-001-figure-01.png]]

<!-- source-page: 2 -->

## Mass

The relation for mass is \(E = mc^2\). The label \(质能方程\) is Chinese.
"""

NORMALIZED = r"""---
type: course-material
source_pages: 2
---

# Example deck

<!-- source-page: 1 -->

## Energy

Einstein wrote $E = mc^2$.

$$
\begin{aligned}
E &= mc^2 \\
p &= mv
\end{aligned}
$$

![[assets/page-001-figure-01.png]]

<!-- source-page: 2 -->

## Mass

The relation for mass is $E = mc^2$. The label $\text{质能方程}$ is Chinese.
"""


class NormalizationTests(unittest.TestCase):
    def test_expected_normalization(self):
        result, stats = NORMALIZER.normalize_text(BASE)
        self.assertEqual(result, NORMALIZED)
        self.assertGreaterEqual(stats["stripped_labels"], 1)
        self.assertGreaterEqual(stats["cjk_runs_wrapped"], 1)

    def test_normalization_is_idempotent(self):
        once, _ = NORMALIZER.normalize_text(BASE)
        twice, _ = NORMALIZER.normalize_text(once)
        self.assertEqual(once, twice)

    def test_inline_parenthesis_delimiters(self):
        result, _ = NORMALIZER.normalize_text("Value \\(x + y\\).")
        self.assertEqual(result, "Value $x + y$.")

    def test_display_bracket_delimiters(self):
        result, _ = NORMALIZER.normalize_text("\\[a^2 + b^2 = c^2\\]")
        self.assertEqual(result, "$$\na^2 + b^2 = c^2\n$$")

    def test_equation_environment_and_label(self):
        result, stats = NORMALIZER.normalize_text("\\begin{equation}\ny = x^2 \\label{eq:one}\n\\end{equation}")
        self.assertEqual(result, "$$\ny = x^2\n$$")
        self.assertEqual(stats["stripped_labels"], 1)

    def test_align_becomes_aligned(self):
        result, _ = NORMALIZER.normalize_text("\\begin{align}a &= b \\\\ c &= d\\end{align}")
        self.assertIn("\\begin{aligned}", result)
        self.assertIn("\\end{aligned}", result)
        self.assertNotIn("\\begin{align}", result)

    def test_gather_becomes_gathered(self):
        result, _ = NORMALIZER.normalize_text("\\begin{gather}x = 1 \\\\ y = 2\\end{gather}")
        self.assertIn("\\begin{gathered}", result)

    def test_cjk_run_is_wrapped(self):
        result, stats = NORMALIZER.normalize_text("$$能量 E$$")
        self.assertEqual(result, "$$\n\\text{能量} E\n$$")
        self.assertEqual(stats["cjk_runs_wrapped"], 1)

    def test_cjk_already_in_text_command_is_unchanged(self):
        result, stats = NORMALIZER.normalize_text("$$E = mc^2 \\quad \\text{质能方程}$$")
        self.assertEqual(result, "$$\nE = mc^2 \\quad \\text{质能方程}\n$$")
        self.assertEqual(stats["cjk_runs_wrapped"], 0)

    def test_cjk_wrapping_can_be_disabled(self):
        result, stats = NORMALIZER.normalize_text("$$质量 m$$", wrap_cjk=False)
        self.assertEqual(result, "$$\n质量 m\n$$")
        self.assertEqual(stats["cjk_runs_wrapped"], 0)

    def test_multiline_inline_is_promoted(self):
        result, stats = NORMALIZER.normalize_text("$a +\nb$")
        self.assertEqual(result, "$$\na +\nb\n$$")
        self.assertEqual(stats["promoted_multiline_inline"], 1)

    def test_fenced_code_is_not_rewritten(self):
        source = "```text\n\\(not math\\)\n```"
        result, stats = NORMALIZER.normalize_text(source)
        self.assertEqual(result, source)
        self.assertEqual(stats["math_spans"], 0)

    def test_inline_code_is_not_rewritten(self):
        source = "Use `\\(x\\)` literally."
        result, stats = NORMALIZER.normalize_text(source)
        self.assertEqual(result, source)
        self.assertEqual(stats["math_spans"], 0)


class ValidationTests(unittest.TestCase):
    def test_normalized_note_is_valid(self):
        result = VALIDATOR.validate_refinement(BASE, NORMALIZED)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["page_markers"], [1, 2])

    def test_visible_text_change_is_rejected(self):
        changed = NORMALIZED.replace("Einstein wrote", "Newton wrote")
        result = VALIDATOR.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("visible non-math text" in item for item in result["errors"]))

    def test_math_change_is_rejected(self):
        changed = NORMALIZED.replace("p &= mv", "q &= mv")
        result = VALIDATOR.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("math content changed" in item for item in result["errors"]))

    def test_added_math_is_rejected(self):
        changed = NORMALIZED.replace("The relation for mass is", "The relation for mass $x$ is")
        result = VALIDATOR.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])

    def test_marker_change_is_rejected(self):
        changed = NORMALIZED.replace("<!-- source-page: 1 -->", "<!--  source-page: 1  -->")
        result = VALIDATOR.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("source-page markers" in item for item in result["errors"]))

    def test_frontmatter_change_is_rejected(self):
        changed = NORMALIZED.replace("source_pages: 2", "source_pages: 3")
        result = VALIDATOR.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertIn("frontmatter changed", result["errors"])

    def test_asset_cross_page_is_rejected(self):
        changed = NORMALIZED.replace(
            "![[assets/page-001-figure-01.png]]\n\n<!-- source-page: 2 -->",
            "<!-- source-page: 2 -->\n\n![[assets/page-001-figure-01.png]]",
        )
        result = VALIDATOR.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("asset set" in item for item in result["errors"]))

    def test_link_change_is_rejected(self):
        base = BASE.replace("## Mass", "## Mass\n\nSee [[Reference Note]].")
        changed = NORMALIZED.replace("## Mass", "## Mass\n\nSee [[Other Note]].")
        result = VALIDATOR.validate_refinement(base, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("link destinations" in item for item in result["errors"]))

    def test_new_callout_is_rejected(self):
        changed = NORMALIZED.replace("## Energy", "> [!note]\n> Note\n\n## Energy")
        result = VALIDATOR.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("Callout headers" in item for item in result["errors"]))

    def test_lecture_layer_stops_normalization(self):
        marker = "<!-- lecture-layer:student:example:start -->\n"
        result = VALIDATOR.validate_refinement(
            BASE.replace("## Energy", marker + "## Energy"),
            NORMALIZED.replace("## Energy", marker + "## Energy"),
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any("student/teacher layers" in item for item in result["errors"]))

    def test_raw_html_is_rejected(self):
        changed = NORMALIZED.replace("The relation for mass is", "<div>The relation for mass is")
        result = VALIDATOR.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("raw HTML" in item for item in result["errors"]))

    def test_unbalanced_dollar_is_reported_for_review(self):
        items = NORMALIZER.review_items("Loose $ sign and no partner.")
        self.assertTrue(any("unbalanced dollar" in item for item in items))

    def test_unsupported_document_latex_is_reported_for_review(self):
        items = NORMALIZER.review_items("\\includegraphics{plot.png}")
        self.assertTrue(any("image command" in item for item in items))


class CliTests(unittest.TestCase):
    def test_cli_normalizes_in_place_without_second_note(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            run = root / "tmp/run-1"
            target = vault / "COURSE101/example.md"
            snapshot = run / "before.md"
            report = run / "latex-refinement-report.json"
            target.parent.mkdir(parents=True)
            run.mkdir(parents=True)
            target.write_text(BASE)
            result = subprocess.run(
                [sys.executable, str(NORMALIZER_SCRIPT), "--target", str(target),
                 "--vault-root", str(vault), "--snapshot", str(snapshot), "--report", str(report)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data["valid"])
            self.assertFalse(data["restored"])
            self.assertEqual(target.read_text(), NORMALIZED)
            self.assertEqual(snapshot.read_text(), BASE)
            self.assertTrue(report.is_file())
            self.assertEqual(list(target.parent.glob("*.md")), [target])

    def test_cli_rolls_back_invalid_overwrite_without_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            run = root / "tmp/run-2"
            target = vault / "COURSE101/example.md"
            snapshot = run / "before.md"
            report = run / "latex-refinement-report.json"
            target.parent.mkdir(parents=True)
            run.mkdir(parents=True)
            snapshot.write_text(BASE)
            target.write_text(NORMALIZED.replace("Einstein wrote", "Newton wrote"))
            result = subprocess.run(
                [sys.executable, str(VALIDATOR_SCRIPT), "--snapshot", str(snapshot),
                 "--target", str(target), "--vault-root", str(vault), "--report", str(report)],
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
            report = root / "tmp/latex-refinement-report.json"
            target.parent.mkdir(parents=True)
            snapshot.parent.mkdir(parents=True)
            report.parent.mkdir(parents=True)
            target.write_text(BASE)
            snapshot.write_text(BASE)
            result = subprocess.run(
                [sys.executable, str(NORMALIZER_SCRIPT), "--target", str(target),
                 "--vault-root", str(vault), "--snapshot", str(snapshot), "--report", str(report)],
                text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside the Obsidian vault", result.stdout)
            self.assertEqual(target.read_text(), BASE)

    def test_cli_without_math_is_a_noop(self):
        note = "---\nsource_pages: 1\n---\n\n# Plain\n\n<!-- source-page: 1 -->\n\nNo math here.\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            run = root / "tmp/run-3"
            target = vault / "COURSE101/plain.md"
            snapshot = run / "before.md"
            report = run / "latex-refinement-report.json"
            target.parent.mkdir(parents=True)
            run.mkdir(parents=True)
            target.write_text(note)
            result = subprocess.run(
                [sys.executable, str(NORMALIZER_SCRIPT), "--target", str(target),
                 "--vault-root", str(vault), "--snapshot", str(snapshot), "--report", str(report)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["transform_counts"]["math_spans"], 0)
            self.assertEqual(target.read_text(), note)


if __name__ == "__main__":
    unittest.main()
