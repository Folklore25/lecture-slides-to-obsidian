"""Contract tests for the model-ready page renderer.

The PDF is built here rather than committed, so the tests are hermetic and the
fixtures stay redistributable. Every test that renders needs poppler and cwebp.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/render-source-pages.py"
RENDER_TOOLS = all(shutil.which(name) for name in ("pdfinfo", "pdftoppm", "cwebp"))


def build_pdf(path: Path, pages: int = 2, width: int = 960, height: int = 540) -> Path:
    """A minimal but genuinely valid PDF, built so the fixture needs no binary blob."""
    objects: list[bytes] = []
    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(pages))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>".encode())
    for index in range(pages):
        content = f"1 0 0 RG 6 w 40 40 m {width - 40} {height - 40} l S".encode()
        page = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
            f"/Contents {4 + index * 2} 0 R /Resources << >> >>"
        ).encode()
        objects.append(page)
        objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    start_xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start_xref}\n%%EOF\n"
    ).encode()
    path.write_bytes(bytes(out))
    return path


class PageSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = build_pdf(self.base / "deck.pdf", pages=5)
        self.out = self.base / "staging/pages"

    def run_renderer(self, *extra: str, expect: int = 0):
        command = [
            sys.executable, str(SCRIPT), str(self.source),
            "--output-dir", str(self.out), *extra,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def test_all_pages_are_selected_by_default(self):
        self.assertEqual(self.run_renderer("--dry-run")["pages"], [1, 2, 3, 4, 5])

    def test_ranges_and_single_pages_parse(self):
        report = self.run_renderer("--pages", "1,3-4", "--dry-run")
        self.assertEqual(report["pages"], [1, 3, 4])

    def test_a_reversed_range_is_normalized(self):
        self.assertEqual(self.run_renderer("--pages", "4-2", "--dry-run")["pages"], [2, 3, 4])

    def test_a_page_outside_the_document_is_a_hard_failure(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.source), "--output-dir", str(self.out),
             "--pages", "1-9", "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside 1..5", result.stderr)

    def test_an_unreadable_page_spec_is_a_hard_failure(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.source), "--output-dir", str(self.out),
             "--pages", "front-matter", "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("unreadable page", result.stderr)

    def test_the_output_directory_must_stay_outside_the_vault(self):
        vault = self.base / "vault"
        (vault / "course/assets").mkdir(parents=True)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.source),
             "--output-dir", str(vault / "course/assets"),
             "--vault-root", str(vault), "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the vault", result.stderr)

    def test_a_source_outside_the_vault_is_accepted(self):
        self.assertEqual(self.run_renderer("--vault-root", str(self.base / "vault"), "--dry-run")["pages"],
                         [1, 2, 3, 4, 5])

    def test_a_non_pdf_source_is_refused(self):
        other = self.base / "slides.pptx"
        other.write_bytes(b"not a pdf")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(other), "--output-dir", str(self.out), "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("must be a PDF", result.stderr)

    def test_a_missing_source_is_refused(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.base / "absent.pdf"),
             "--output-dir", str(self.out), "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)

    def test_an_edge_ceiling_above_the_harness_cap_is_refused(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.source), "--output-dir", str(self.out),
             "--max-edge", "2400", "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("larger ceiling", result.stderr)

    def test_an_out_of_range_quality_is_refused(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.source), "--output-dir", str(self.out),
             "--quality", "0", "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)

    def test_dry_run_resolves_the_plan_and_writes_nothing(self):
        report = self.run_renderer("--dry-run")
        self.assertEqual(report["rendered"], [])
        self.assertEqual(report["policy"]["quality"], 82)
        self.assertFalse(self.out.exists())


@unittest.skipUnless(RENDER_TOOLS, "poppler and cwebp are required")
class RenderedPageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = build_pdf(self.base / "deck.pdf", pages=3, width=960, height=540)
        self.out = self.base / "staging/pages"

    def run_renderer(self, *extra: str, expect: int = 0):
        command = [
            sys.executable, str(SCRIPT), str(self.source),
            "--output-dir", str(self.out), *extra,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def dimensions(self, path: Path) -> tuple[int, int]:
        header = path.read_bytes()
        start = header.find(b"VP8 ")
        self.assertGreater(start, 0, "the delivered page is not a lossy WebP")
        return (
            int.from_bytes(header[start + 14:start + 16], "little") & 0x3FFF,
            int.from_bytes(header[start + 16:start + 18], "little") & 0x3FFF,
        )

    def test_every_page_is_delivered_as_webp_inside_the_ceiling(self):
        report = self.run_renderer()
        self.assertEqual(report["failed"], [])
        self.assertEqual([entry["page"] for entry in report["rendered"]], [1, 2, 3])
        self.assertEqual(
            sorted(path.name for path in self.out.iterdir()),
            ["page-001.webp", "page-002.webp", "page-003.webp"],
        )
        for entry in report["rendered"]:
            page = self.out / entry["file"]
            self.assertEqual(page.read_bytes()[:4], b"RIFF")
            self.assertEqual(page.read_bytes()[8:12], b"WEBP")
            self.assertEqual(self.dimensions(page), tuple(entry["dimensions"]))
            self.assertLessEqual(max(entry["dimensions"]), 2000)
            self.assertEqual(page.stat().st_size, entry["bytes"])

    def test_the_report_states_the_request_body_budget(self):
        report = self.run_renderer()
        self.assertEqual(report["base64_bytes"], sum(4 * ((e["bytes"] + 2) // 3) for e in report["rendered"]))
        self.assertGreater(report["base64_bytes"], report["bytes"])
        self.assertEqual(report["bytes"], sum(e["bytes"] for e in report["rendered"]))

    def test_no_png_is_left_in_the_output_directory(self):
        self.run_renderer()
        self.assertEqual([path.suffix for path in self.out.iterdir()], [".webp"] * 3)

    def test_rendering_the_same_source_twice_changes_nothing(self):
        first = self.run_renderer()
        before = {path.name: path.read_bytes() for path in self.out.iterdir()}
        second = self.run_renderer()
        self.assertEqual(second["rendered"], [])
        self.assertEqual([entry["page"] for entry in second["skipped"]], [1, 2, 3])
        self.assertEqual({path.name: path.read_bytes() for path in self.out.iterdir()}, before)
        self.assertEqual(second["bytes"], 0)

    def test_a_different_page_file_is_a_collision(self):
        self.run_renderer()
        (self.out / "page-002.webp").write_bytes(b"RIFF----WEBPVP8 stale")
        report = self.run_renderer(expect=1)
        self.assertIn("already exists with different bytes", report["failed"][0]["reason"])
        self.assertEqual((self.out / "page-002.webp").read_bytes(), b"RIFF----WEBPVP8 stale")

    def test_a_tall_page_drops_the_dpi_to_fit_the_ceiling(self):
        tall = build_pdf(self.base / "tall.pdf", pages=1, width=612, height=1584)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(tall), "--output-dir", str(self.out),
             "--max-edge", "1200", "--report", str(self.base / "report.json")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((self.base / "report.json").read_text())
        self.assertLess(report["policy"]["dpi"], 150)
        page = self.out / "page-001.webp"
        self.assertLessEqual(max(self.dimensions(page)), 1200)

    def test_a_wide_page_keeps_the_requested_dpi(self):
        report = self.run_renderer()
        self.assertEqual(report["policy"]["dpi"], 150)
        self.assertEqual(report["rendered"][0]["dimensions"], [2000, 1125])

    def test_a_forced_high_dpi_is_still_clamped_to_the_ceiling(self):
        report = self.run_renderer("--dpi", "400")
        self.assertEqual(report["policy"]["dpi"], 150)
        for entry in report["rendered"]:
            self.assertLessEqual(max(entry["dimensions"]), 2000)


if __name__ == "__main__":
    unittest.main()
