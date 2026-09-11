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
SELF_CHECK = SCRIPTS / "self-check.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("latex_validator_under_test", VALIDATOR_SCRIPT)
NORMALIZER = load_module("latex_normalizer_under_test", NORMALIZER_SCRIPT)


def normalize(text, only=None, no_cjk=False):
    enabled = NORMALIZER.parse_only(only, no_cjk)
    return NORMALIZER.normalize_text(text, enabled)


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

SHELL = "$$\n$$\nE = mc^2\n$$\n$$"
SHELL_COLLAPSED = "$$\nE = mc^2\n$$"


class NormalizationTests(unittest.TestCase):
    def test_expected_normalization(self):
        result, stats = normalize(BASE)
        self.assertEqual(result, NORMALIZED)
        self.assertGreaterEqual(stats["stripped_labels"], 1)
        self.assertGreaterEqual(stats["cjk_runs_wrapped"], 1)

    def test_normalization_is_idempotent(self):
        once, _ = normalize(BASE)
        twice, _ = normalize(once)
        self.assertEqual(once, twice)

    def test_inline_parenthesis_delimiters(self):
        result, _ = normalize("Value \\(x + y\\).")
        self.assertEqual(result, "Value $x + y$.")

    def test_display_bracket_delimiters(self):
        result, _ = normalize("\\[a^2 + b^2 = c^2\\]")
        self.assertEqual(result, "$$\na^2 + b^2 = c^2\n$$")

    def test_equation_environment_and_label(self):
        result, stats = normalize("\\begin{equation}\ny = x^2 \\label{eq:one}\n\\end{equation}")
        self.assertEqual(result, "$$\ny = x^2\n$$")
        self.assertEqual(stats["stripped_labels"], 1)

    def test_align_becomes_aligned(self):
        result, _ = normalize("\\begin{align}a &= b \\\\ c &= d\\end{align}")
        self.assertIn("\\begin{aligned}", result)
        self.assertNotIn("\\begin{align}", result)

    def test_gather_becomes_gathered(self):
        result, _ = normalize("\\begin{gather}x = 1 \\\\ y = 2\\end{gather}")
        self.assertIn("\\begin{gathered}", result)

    def test_redundant_display_shell_is_collapsed(self):
        result, stats = normalize(SHELL)
        self.assertEqual(result, SHELL_COLLAPSED)
        self.assertEqual(stats["redundant_display_shells_collapsed"], 1)
        self.assertEqual(stats["empty_math_skipped"], 0)

    def test_redundant_display_shell_is_conserved(self):
        collapsed, _ = normalize(SHELL)
        result = VALIDATOR.validate_refinement(
            "---\nsource_pages: 1\n---\n\n# T\n\n<!-- source-page: 1 -->\n\n" + SHELL + "\n",
            "---\nsource_pages: 1\n---\n\n# T\n\n<!-- source-page: 1 -->\n\n" + collapsed + "\n",
        )
        self.assertTrue(result["valid"], result["errors"])

    def test_cjk_run_is_wrapped(self):
        result, stats = normalize("$$能量 E$$")
        self.assertEqual(result, "$$\n\\text{能量} E\n$$")
        self.assertEqual(stats["cjk_runs_wrapped"], 1)

    def test_cjk_already_in_text_command_is_unchanged(self):
        result, stats = normalize("$$E = mc^2 \\quad \\text{质能方程}$$")
        self.assertEqual(result, "$$\nE = mc^2 \\quad \\text{质能方程}\n$$")
        self.assertEqual(stats["cjk_runs_wrapped"], 0)

    def test_multiline_inline_is_promoted(self):
        result, stats = normalize("$a +\nb$")
        self.assertEqual(result, "$$\na +\nb\n$$")
        self.assertEqual(stats["promoted_multiline_inline"], 1)

    def test_only_labels_leaves_delimiters_untouched(self):
        result, stats = normalize("$x\\label{a}$", only="labels")
        self.assertEqual(result, "$x$")
        self.assertEqual(stats["inline_parenthesis_delimiters"], 0)
        self.assertEqual(stats["stripped_labels"], 1)

    def test_only_shell_leaves_cjk_untouched(self):
        result, stats = normalize(SHELL, only="shell")
        self.assertEqual(result, SHELL_COLLAPSED)
        self.assertEqual(stats["cjk_runs_wrapped"], 0)

    def test_no_cjk_disables_wrapping(self):
        result, stats = normalize("$$质量 m$$", no_cjk=True)
        self.assertEqual(result, "$$\n质量 m\n$$")
        self.assertEqual(stats["cjk_runs_wrapped"], 0)

    def test_unknown_only_group_is_rejected(self):
        with self.assertRaises(NORMALIZER.V.RefinementError):
            NORMALIZER.parse_only("nonsense", False)

    def test_fenced_code_is_not_rewritten(self):
        source = "```text\n\\(not math\\)\n```"
        result, stats = normalize(source)
        self.assertEqual(result, source)
        self.assertEqual(stats["math_spans"], 0)

    def test_inline_code_is_not_rewritten(self):
        source = "Use `\\(x\\)` literally."
        result, stats = normalize(source)
        self.assertEqual(result, source)
        self.assertEqual(stats["math_spans"], 0)


class AnalysisTests(unittest.TestCase):
    def test_analysis_detects_shell_and_legacy_delimiters(self):
        analysis = NORMALIZER.analyze_text(
            "---\nsource_pages: 1\n---\n\n# T\n\n<!-- source-page: 1 -->\n\n" + SHELL + "\n\nAnd \\(a+b\\).\n",
            "note.md",
        )
        self.assertEqual(analysis["totals"]["redundant_display_shell"], 1)
        self.assertEqual(analysis["totals"]["legacy_inline_delimiter"], 1)
        self.assertIn("shell", analysis["recommended_transforms"])
        self.assertIn("delimiters", analysis["recommended_transforms"])

    def test_analysis_reports_document_latex_as_review(self):
        analysis = NORMALIZER.analyze_text("\\includegraphics{plot.png}", "note.md")
        self.assertEqual(analysis["totals"]["document_latex_image"], 1)
        self.assertTrue(any("image command" in item for item in analysis["review_items"]))

    def test_analysis_reports_unbalanced_dollar(self):
        analysis = NORMALIZER.analyze_text("Loose $ sign here.", "note.md")
        self.assertEqual(analysis["totals"]["unbalanced_dollar"], 1)


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

    def test_math_change_reports_first_difference(self):
        changed = NORMALIZED.replace("p &= mv", "q &= mv")
        result = VALIDATOR.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        page_one = next(page for page in result["pages"] if page["page"] == 1)
        self.assertIn("vs refined", page_one["math_difference"])

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

    def test_new_callout_is_rejected(self):
        changed = NORMALIZED.replace("## Energy", "> [!note]\n> Note\n\n## Energy")
        result = VALIDATOR.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("Callout headers" in item for item in result["errors"]))

    def test_lecture_layer_blocks_by_default(self):
        marker = "<!-- lecture-layer:student:example:start -->\n"
        result = VALIDATOR.validate_refinement(
            BASE.replace("## Energy", marker + "## Energy"),
            NORMALIZED.replace("## Energy", marker + "## Energy"),
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any("student/teacher layers" in item for item in result["errors"]))

    def test_allow_lecture_layers_permits_math_only_pass(self):
        marker = "<!-- lecture-layer:student:example:start -->\n"
        result = VALIDATOR.validate_refinement(
            BASE.replace("## Energy", marker + "## Energy"),
            NORMALIZED.replace("## Energy", marker + "## Energy"),
            allow_lecture_layers=True,
        )
        self.assertTrue(result["valid"], result["errors"])
        self.assertTrue(result["lecture_layers_present"])

    def test_raw_html_is_rejected(self):
        changed = NORMALIZED.replace("The relation for mass is", "<div>The relation for mass is")
        result = VALIDATOR.validate_refinement(BASE, changed)
        self.assertFalse(result["valid"])
        self.assertTrue(any("raw HTML" in item for item in result["errors"]))

    def test_summary_is_human_readable(self):
        result = VALIDATOR.validate_refinement(BASE, NORMALIZED)
        summary = VALIDATOR.summarize(result)
        self.assertTrue(summary[0].startswith("valid:"))


class CliTests(unittest.TestCase):
    def test_self_check_fixtures_pass(self):
        result = subprocess.run(
            [sys.executable, str(SELF_CHECK)], text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("7/7 cases passed", result.stdout)

    def test_cli_analyze_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            (vault / ".obsidian").mkdir(parents=True)
            target = vault / "note.md"
            target.write_text("---\nsource_pages: 1\n---\n\n# T\n\n<!-- source-page: 1 -->\n\n" + SHELL + "\n\n\\(a+b\\)\n")
            before = target.read_text()
            result = subprocess.run(
                [sys.executable, str(NORMALIZER_SCRIPT), "--target", str(target), "--analyze"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["mode"], "analyze")
            self.assertEqual(target.read_text(), before)

    def test_cli_normalizes_in_place_and_autodetects_vault(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            (vault / ".obsidian").mkdir(parents=True)
            target = vault / "note.md"
            snapshot = root / "before.md"
            report = root / "latex-refinement-report.json"
            target.write_text("---\nsource_pages: 1\n---\n\n# T\n\n<!-- source-page: 1 -->\n\n" + SHELL + "\n")
            result = subprocess.run(
                [sys.executable, str(NORMALIZER_SCRIPT), "--target", str(target),
                 "--snapshot", str(snapshot), "--report", str(report)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["vault_root_source"], "detected")
            self.assertIn(SHELL_COLLAPSED, target.read_text())
            self.assertEqual(snapshot.read_text(), "---\nsource_pages: 1\n---\n\n# T\n\n<!-- source-page: 1 -->\n\n" + SHELL + "\n")
            self.assertEqual(list(target.parent.glob("*.md")), [target])

    def test_cli_dry_run_does_not_touch_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            (vault / ".obsidian").mkdir(parents=True)
            target = vault / "note.md"
            snapshot = root / "before.md"
            report = root / "latex-refinement-report.json"
            original = "---\nsource_pages: 1\n---\n\n# T\n\n<!-- source-page: 1 -->\n\n" + SHELL + "\n"
            target.write_text(original)
            result = subprocess.run(
                [sys.executable, str(NORMALIZER_SCRIPT), "--target", str(target),
                 "--snapshot", str(snapshot), "--report", str(report), "--dry-run"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(target.read_text(), original)
            self.assertTrue(data["would_be_valid"])
            self.assertTrue(Path(data["proposed_path"]).is_file())

    def test_cli_text_report_format(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            (vault / ".obsidian").mkdir(parents=True)
            target = vault / "note.md"
            target.write_text("---\nsource_pages: 1\n---\n\n# T\n\n<!-- source-page: 1 -->\n\n\\(a+b\\)\n")
            result = subprocess.run(
                [sys.executable, str(NORMALIZER_SCRIPT), "--target", str(target),
                 "--snapshot", str(root / "before.md"), "--report", str(root / "r.json"),
                 "--report-format", "text"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("valid: yes", result.stdout)
            self.assertFalse(result.stdout.lstrip().startswith("{"))

    def test_cli_rolls_back_invalid_overwrite_without_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            (vault / ".obsidian").mkdir(parents=True)
            target = vault / "note.md"
            snapshot = root / "before.md"
            report = root / "latex-refinement-report.json"
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


if __name__ == "__main__":
    unittest.main()
