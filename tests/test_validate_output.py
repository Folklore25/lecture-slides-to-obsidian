import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
VALIDATOR = REPO / "skills/lecture-slides-to-obsidian/scripts/validate-output.py"
FIXTURE = REPO / "tests/fixtures/synthetic/valid-document-folder"
REPORT_FIXTURE = REPO / "tests/fixtures/staging/conversion-report.md"


def webp_bytes(width: int, height: int) -> bytes:
    """A lossy WebP header carrying the given canvas size, which is all a gate reads."""
    payload = (
        bytes(3) + bytes((0x9D, 0x01, 0x2A))
        + (width).to_bytes(2, "little") + (height).to_bytes(2, "little")
    )
    return (
        b"RIFF" + (len(payload) + 4).to_bytes(4, "little") + b"WEBP"
        + b"VP8 " + (len(payload)).to_bytes(4, "little") + payload
    )


def run_validator(
    folder: Path,
    report: Path = REPORT_FIXTURE,
    delete_report: bool = False,
    vault_root: Path | None = None,
    recall_model: Path | None = None,
    latex_refinement_report: Path | None = None,
    aesthetic_check: Path | None = None,
    render_metrics: Path | None = None,
    render_check: Path | None = None,
) -> tuple[int, dict]:
    command = [sys.executable, str(VALIDATOR), str(folder), "--report", str(report)]
    if vault_root is None:
        command.append("--fixture-mode")
    else:
        command += ["--vault-root", str(vault_root)]
    if recall_model is not None:
        command += ["--recall-model", str(recall_model)]
    if latex_refinement_report is not None:
        command += ["--latex-refinement-report", str(latex_refinement_report)]
    if aesthetic_check is not None:
        command += ["--aesthetic-check", str(aesthetic_check)]
    if render_metrics is not None:
        command += ["--render-metrics", str(render_metrics)]
    if render_check is not None:
        command += ["--render-check", str(render_check)]
    if delete_report:
        command.append("--delete-report-on-success")
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, json.loads(result.stdout)


def write_canvas_qa(staging: Path, canvas: Path) -> tuple[Path, Path, Path]:
    canvas_hash = hashlib.sha256(canvas.read_bytes()).hexdigest()
    aesthetic = staging / "canvas-aesthetic-check.json"
    metrics = staging / "canvas-render-metrics.json"
    check = staging / "canvas-render-check.json"
    aesthetic.write_text(json.dumps({
        "schema_version": 1,
        "valid": True,
        "score": 100,
        "minimum_score": 85,
        "canvas_sha256": canvas_hash,
    }))
    metrics.write_text(json.dumps({
        "schema_version": 1,
        "mode": "measure",
        "measurement_complete": True,
        "nodes": [{"id": "synthetic", "required_height": 300}],
    }))
    check.write_text(json.dumps({
        "schema_version": 1,
        "mode": "check",
        "measurement_complete": True,
        "valid": True,
        "canvas_sha256": canvas_hash,
    }))
    return aesthetic, metrics, check


class ImageDimensionTests(unittest.TestCase):
    """The dimension reader decides which axis a delivered asset is bounded on."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("validate_output", VALIDATOR)
        cls.validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.validator)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def write(self, name: str, payload: bytes) -> Path:
        path = self.folder / name
        path.write_bytes(payload)
        return path

    def test_a_jpeg_reports_width_before_height(self):
        # SOI, APP0, then a start-of-frame whose segment stores height before width.
        payload = (
            b"\xff\xd8"
            + b"\xff\xe0" + (16).to_bytes(2, "big") + bytes(14)
            + b"\xff\xc0" + (17).to_bytes(2, "big") + b"\x08"
            + (1200).to_bytes(2, "big") + (1600).to_bytes(2, "big")
        )
        path = self.write("figure.jpg", payload)
        self.assertEqual(self.validator.image_dimensions(path), (1600, 1200))

    def test_a_webp_reports_its_canvas_size(self):
        payload = (
            b"RIFF" + (30).to_bytes(4, "little") + b"WEBP"
            + b"VP8 " + (10).to_bytes(4, "little")
            + b"\x00\x00\x00" + bytes((0x9D, 0x01, 0x2A))
            + (1600).to_bytes(2, "little") + (900).to_bytes(2, "little")
        )
        path = self.write("figure.webp", payload)
        self.assertEqual(self.validator.image_dimensions(path), (1600, 900))

    def test_a_lossless_webp_reports_its_canvas_size(self):
        bits = 1199 | (899 << 14)
        payload = (
            b"RIFF" + (26).to_bytes(4, "little") + b"WEBP"
            + b"VP8L" + (5).to_bytes(4, "little") + b"\x2f" + bits.to_bytes(4, "little")
        )
        path = self.write("flat.webp", payload)
        self.assertEqual(self.validator.image_dimensions(path), (1200, 900))

    def test_an_extended_webp_reports_its_canvas_size(self):
        payload = (
            b"RIFF" + (40).to_bytes(4, "little") + b"WEBP"
            + b"VP8X" + (10).to_bytes(4, "little")
            + bytes(4) + (1599).to_bytes(3, "little") + (899).to_bytes(3, "little")
        )
        path = self.write("animated.webp", payload)
        self.assertEqual(self.validator.image_dimensions(path), (1600, 900))

    def test_a_truncated_webp_is_reported_as_unreadable(self):
        path = self.write("broken.webp", b"RIFF" + (4).to_bytes(4, "little") + b"WEBP")
        self.assertIsNone(self.validator.image_dimensions(path))


class MathJaxLintTests(unittest.TestCase):
    """The MathJax gate. Obsidian renders math with MathJax, so $...$ and $$...$$ only."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("validate_output", VALIDATOR)
        cls.validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.validator)

    def lint(self, text: str) -> list[str]:
        return self.validator.validate_note_math(text, "n.md")

    def test_standard_mathjax_passes(self):
        self.assertEqual(self.lint("Choose $k$ clusters.\n\n$$\nd(x, y) = " + chr(92) + "sqrt{" + chr(92) + "sum_{i=1}^{n} (x_i - y_i)^2}\n$$\n"), [])

    def test_the_mathjax_environments_pass(self):
        text = (
            "$$\n" + chr(92) + "begin{aligned}\na &= b " + chr(92) + chr(92) + "\n"
            + chr(92) + "end{aligned}\n$$\n\n$$" + chr(92) + "begin{gathered} x = y "
            + chr(92) + "end{gathered}$$\n\n" + "$$\\begin{cases} a & b \\\\end{cases}$$\n"
        )
        self.assertEqual(self.lint(text), [])

    def test_a_text_command_carries_its_own_words(self):
        self.assertEqual(self.lint("$$d(" + chr(92) + "text{apple}, " + chr(92) + "text{orange})$$"), [])

    def test_operators_legitimately_written_bare_pass(self):
        self.assertEqual(self.lint("$log x$, $exp(y)$, $\\lim_{n}$, $max k$, $\\sin x$"), [])

    def test_currency_is_not_math(self):
        for text in ("a $15 minimum wage", "income above $75,000 per year", "**+HK$163.66.**"):
            self.assertEqual(self.lint(text), [], text)

    def test_math_that_starts_with_a_digit_is_math(self):
        self.assertEqual(self.lint("multiplying by $1/(n-1)$ rescales"), [])

    def test_a_lost_backslash_is_reported_with_the_symbol_it_erased(self):
        errors = self.lint("$$d(x, y) = sqrt{sum_{i=1}^{n} (x_i - y_i)^2}$$")
        self.assertEqual(len(errors), 2)
        self.assertIn("must see √", errors[0])
        self.assertIn("must see ∑", errors[1])

    def test_a_tab_inside_math_is_reported_as_an_interpreted_escape(self):
        self.assertTrue(any("tab" in item for item in self.lint("$$d(" + chr(9) + "ext{apple})$$")))

    def test_a_form_feed_inside_math_is_reported_as_an_interpreted_escape(self):
        self.assertTrue(any("form feed" in item for item in self.lint("$$z = " + chr(12) + "rac{X - mu}{sigma}$$")))

    def test_a_latex_environment_inside_math_is_rejected(self):
        errors = self.lint("$$\n" + chr(92) + "begin{eqnarray}E = mc^2" + chr(92) + chr(92) + chr(92) + chr(92) + "\n" + chr(92) + "end{eqnarray}\n$$")
        self.assertTrue(any("eqnarray" in item for item in errors))

    def test_a_non_rendering_command_is_rejected(self):
        for command in ("label{eq:one}", "nonumber", "notag", "hline"):
            errors = self.lint("$$x = y " + chr(92) + command + "$$")
            self.assertTrue(errors, command)

    def test_raw_cjk_inside_math_is_rejected(self):
        self.assertTrue(any("CJK" in item for item in self.lint("$$" + chr(92) + "text{ok} 总收益 = 1$$")))

    def test_document_latex_in_prose_is_rejected(self):
        self.assertTrue(any("includegraphics" in item for item in self.lint("See " + chr(92) + "includegraphics{plot.pdf} for the figure.")))

    def test_an_environment_outside_math_is_rejected(self):
        errors = self.lint(chr(92) + "begin{align} x &= y " + chr(92) + "end{align}")
        self.assertTrue(any("not inside a math span" in item for item in errors))

    def test_an_empty_display_block_is_rejected(self):
        self.assertTrue(any("empty math span" in item for item in self.lint("$$\n$$")))

    def test_inline_math_spanning_a_line_break_is_rejected(self):
        self.assertTrue(any("line break" in item for item in self.lint("cost $a + b\n+ c$ dollars")))

    def test_an_unclosed_delimiter_is_reported_with_its_line(self):
        errors = self.lint("---\ntype: course-material\n---\n\n# T\n\ntext $x and more\n")
        self.assertTrue(any("line 7" in item for item in errors), errors)

    def test_latex_in_a_code_block_is_not_math(self):
        text = "```\n" + chr(92) + "begin{align}\n$$x$$\n```\n\nand $y$ is fine\n"
        self.assertEqual(self.lint(text), [])

    def test_inline_code_holding_dollars_is_not_math(self):
        self.assertEqual(self.lint("use `$var` and `$other` in the shell"), [])

    def test_frontmatter_dollars_are_not_math(self):
        self.assertEqual(self.lint("---\ntitle: A $5 note\n---\n\nbody $k$ here\n"), [])

    def test_the_gate_never_writes(self):
        original = "$$d(x,y) = sqrt{sum x_i}$$"
        before = original
        self.lint(original)
        self.assertEqual(original, before)


class ValidateOutputTests(unittest.TestCase):
    def test_valid_fixture_passes(self):
        code, result = run_validator(FIXTURE)
        self.assertEqual(code, 0)
        self.assertTrue(result["valid"])

    def test_source_original_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            (folder / "source.pdf").write_bytes(b"synthetic invalid fixture")
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("source originals" in item for item in result["errors"]))

    def test_page_marker_out_of_range_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            note = folder / "sample.md"
            note.write_text(note.read_text().replace("source-page: 2", "source-page: 3"))
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("outside 1..2" in item for item in result["errors"]))

    def test_dangling_canvas_edge_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            canvas_path = folder / "sample.canvas"
            canvas = json.loads(canvas_path.read_text())
            canvas["edges"][0]["toNode"] = "ffffffffffffffff"
            canvas_path.write_text(json.dumps(canvas))
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("dangling toNode" in item for item in result["errors"]))

    def test_generic_canvas_relation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            canvas_path = folder / "sample.canvas"
            canvas = json.loads(canvas_path.read_text())
            concept_ids = {
                node["id"] for node in canvas["nodes"]
                if "<!-- recall-map: concept -->" in node.get("text", "")
            }
            semantic_edge = next(
                edge for edge in canvas["edges"]
                if edge["fromNode"] in concept_ids and edge["toNode"] in concept_ids
            )
            semantic_edge["label"] = "related to"
            canvas_path.write_text(json.dumps(canvas))
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("structural/generic label" in item for item in result["errors"]))

    def test_missing_one_minute_overview_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            canvas_path = folder / "sample.canvas"
            canvas = json.loads(canvas_path.read_text())
            overview = next(
                node for node in canvas["nodes"]
                if "<!-- recall-map: overview -->" in node.get("text", "")
            )
            overview["text"] = overview["text"].replace("<!-- recall-map: overview -->", "")
            canvas_path.write_text(json.dumps(canvas))
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("exactly one overview" in item for item in result["errors"]))

    def test_stale_render_check_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            folder = base / "document"
            staging = base / "staging"
            report = staging / "conversion-report.md"
            shutil.copytree(FIXTURE, folder)
            staging.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            aesthetic_check, render_metrics, render_check = write_canvas_qa(staging, folder / "sample.canvas")
            check = json.loads(render_check.read_text())
            check["canvas_sha256"] = "0" * 64
            render_check.write_text(json.dumps(check))
            code, result = run_validator(
                folder, report, aesthetic_check=aesthetic_check,
                render_metrics=render_metrics, render_check=render_check,
            )
            self.assertNotEqual(code, 0)
            self.assertTrue(any("does not match the delivered Canvas" in item for item in result["errors"]))

    def test_stale_aesthetic_check_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            folder = base / "document"
            staging = base / "staging"
            report = staging / "conversion-report.md"
            shutil.copytree(FIXTURE, folder)
            staging.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            aesthetic_check, render_metrics, render_check = write_canvas_qa(
                staging, folder / "sample.canvas"
            )
            aesthetic = json.loads(aesthetic_check.read_text())
            aesthetic["canvas_sha256"] = "0" * 64
            aesthetic_check.write_text(json.dumps(aesthetic))
            code, result = run_validator(
                folder, report, aesthetic_check=aesthetic_check,
                render_metrics=render_metrics, render_check=render_check,
            )
            self.assertNotEqual(code, 0)
            self.assertTrue(any("aesthetic check does not match" in item for item in result["errors"]))

    def test_optional_latex_report_must_match_delivered_markdown(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            folder = base / "document"
            staging = base / "staging"
            report = staging / "conversion-report.md"
            latex_report = staging / "latex-refinement-report.json"
            shutil.copytree(FIXTURE, folder)
            staging.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            note_hash = hashlib.sha256((folder / "sample.md").read_bytes()).hexdigest()
            latex_report.write_text(json.dumps({
                "schema_version": 1,
                "valid": True,
                "snapshot_sha256": "a" * 64,
                "refined_sha256": note_hash,
            }))
            code, result = run_validator(
                folder, report, latex_refinement_report=latex_report
            )
            self.assertEqual(code, 0, result["errors"])

            stale = json.loads(latex_report.read_text())
            stale["refined_sha256"] = "0" * 64
            latex_report.write_text(json.dumps(stale))
            code, result = run_validator(
                folder, report, latex_refinement_report=latex_report
            )
            self.assertNotEqual(code, 0)
            self.assertTrue(any("does not match the delivered Markdown" in item for item in result["errors"]))

    def test_rejected_latex_report_is_fatal(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            folder = base / "document"
            staging = base / "staging"
            report = staging / "conversion-report.md"
            latex_report = staging / "latex-refinement-report.json"
            shutil.copytree(FIXTURE, folder)
            staging.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            latex_report.write_text(json.dumps({
                "schema_version": 1,
                "valid": False,
                "refined_sha256": hashlib.sha256((folder / "sample.md").read_bytes()).hexdigest(),
            }))
            code, result = run_validator(
                folder, report, latex_refinement_report=latex_report
            )
            self.assertNotEqual(code, 0)
            self.assertTrue(any("LaTeX refinement did not pass" in item for item in result["errors"]))

    def test_temporary_report_is_deleted_on_success(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            report = Path(temp) / "staging" / "conversion-report.md"
            shutil.copytree(FIXTURE, folder)
            report.parent.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            code, result = run_validator(folder, report, delete_report=True)
            self.assertEqual(code, 0)
            self.assertTrue(result["report_deleted"])
            self.assertFalse(report.exists())

    def test_report_inside_document_folder_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            report = folder / "conversion-report.md"
            shutil.copy2(REPORT_FIXTURE, report)
            code, result = run_validator(folder, report)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("outside the document folder" in item for item in result["errors"]))

    def test_dot_prefixed_workflow_folder_in_document_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "document"
            report = root / "tmp/conversion-report.md"
            shutil.copytree(FIXTURE, folder)
            (folder / ".staging").mkdir()
            (folder / ".staging/before.md").write_text("temporary")
            report.parent.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            code, result = run_validator(folder, report)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("dot-prefixed" in item for item in result["errors"]))

    def test_degenerate_crop_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            # A 900x30 strip: the classic "table edge" crop that still resolves and embeds.
            (folder / "assets/page-001-figure-01.webp").write_bytes(webp_bytes(900, 30))
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("cannot carry its subject" in item for item in result["errors"]))

    def test_a_normal_figure_size_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            (folder / "assets/page-001-figure-01.webp").write_bytes(webp_bytes(1200, 700))
            code, result = run_validator(folder)
            self.assertEqual(code, 0, result["errors"])

    def test_an_unoptimized_page_render_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            # A 2400px full-page render: what an extraction drops in when nothing bounds it.
            (folder / "assets/page-001-figure-01.webp").write_bytes(webp_bytes(2400, 1500))
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("optimize-assets.py" in item for item in result["errors"]))

    def test_a_leftover_png_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            # Small enough to pass every dimension gate, and still the wrong format.
            (folder / "assets/page-001-figure-01.png").write_bytes(webp_bytes(1200, 700))
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("optimize-assets.py" in item for item in result["errors"]))

    def test_standardized_asset_name_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            (folder / "assets/page-001-figure-01.webp").write_bytes(webp_bytes(1200, 700))
            code, result = run_validator(folder)
            self.assertEqual(code, 0, result["errors"])
            self.assertTrue(result["valid"])

    def test_unstandardized_asset_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            (folder / "assets/figure.png").write_bytes(b"synthetic")
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("page-PPP-kind-NN.ext" in item for item in result["errors"]))

    def test_asset_sequence_gap_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "document"
            shutil.copytree(FIXTURE, folder)
            (folder / "assets/page-001-figure-01.webp").write_bytes(b"synthetic")
            (folder / "assets/page-001-figure-03.webp").write_bytes(b"synthetic")
            code, result = run_validator(folder)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("contiguous from 01" in item for item in result["errors"]))

    def test_vault_relative_canvas_path_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            vault = base / "vault"
            folder = vault / "COURSE101/Lectures/sample"
            report = base / "staging/conversion-report.md"
            recall_model = base / "staging/recall-model.json"
            shutil.copytree(FIXTURE, folder)
            report.parent.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            recall_model.write_text('{"schema_version":1}')
            canvas_path = folder / "sample.canvas"
            canvas = json.loads(canvas_path.read_text())
            note_node = next(
                node for node in canvas["nodes"]
                if node.get("type") == "file" and node.get("file", "").endswith(".md")
            )
            note_node["file"] = "COURSE101/Lectures/sample/sample.md"
            canvas_path.write_text(json.dumps(canvas))
            aesthetic_check, render_metrics, render_check = write_canvas_qa(report.parent, canvas_path)
            code, result = run_validator(
                folder, report, vault_root=vault, recall_model=recall_model,
                aesthetic_check=aesthetic_check,
                render_metrics=render_metrics, render_check=render_check,
            )
            self.assertEqual(code, 0)
            self.assertTrue(result["valid"])

    def test_bare_canvas_filename_fails_with_vault_root(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            vault = base / "vault"
            folder = vault / "COURSE101/Lectures/sample"
            report = base / "staging/conversion-report.md"
            recall_model = base / "staging/recall-model.json"
            shutil.copytree(FIXTURE, folder)
            report.parent.mkdir()
            shutil.copy2(REPORT_FIXTURE, report)
            recall_model.write_text('{"schema_version":1}')
            aesthetic_check, render_metrics, render_check = write_canvas_qa(report.parent, folder / "sample.canvas")
            code, result = run_validator(
                folder, report, vault_root=vault, recall_model=recall_model,
                aesthetic_check=aesthetic_check,
                render_metrics=render_metrics, render_check=render_check,
            )
            self.assertNotEqual(code, 0)
            self.assertTrue(any("file node unresolved" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
