"""Contract tests for the delivered-asset WebP optimizer.

The encoder is a byte-level stub so the policy decisions stay deterministic: which
files are re-encoded, which resize box is requested, when a file is left alone, and
when an original survives. One test drives the real cwebp when the machine has it.
"""

import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/optimize-assets.py"
PNG_MAGIC = bytes((0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A))

STUB = r"""#!{python}
import struct, sys, zlib
from pathlib import Path

MAGIC = bytes((0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A))
argv = sys.argv[1:]
Path({log!r}).write_text(" ".join(argv))
output = Path(argv[argv.index("-o") + 1])
raw = Path(argv[-1]).read_bytes()
width, height = int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
if "-resize" in argv:
    index = argv.index("-resize")
    if argv[index + 1] == "0":
        height = max(1, round(height * int(argv[index + 2]) / width))
    else:
        width = max(1, round(width * int(argv[index + 2]) / height))

def chunk(tag, payload):
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", zlib.crc32(tag + payload)))

header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
body = (MAGIC + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(b""))
        + chunk(b"IEND", b""))
if {grow!r}:
    body = body + bytes({extra!r})
output.write_bytes(body)
"""


def solid_png(width: int, height: int) -> bytes:
    """A deterministic truecolour PNG built with the stdlib, like the repo fixtures."""
    raw = b"".join(b"\x00" + b"\x20\x60\xa0" * width for _ in range(height))

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload))
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        PNG_MAGIC
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class OptimizerTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.vault = self.base / "vault"
        self.folder = self.vault / "COURSE101/Lectures/week3-research"
        self.assets = self.folder / "assets"
        self.assets.mkdir(parents=True)
        self.log = self.base / "argv.log"
        self.encoder = self.write_encoder(grow=False, extra=0)

    def write_encoder(self, grow: bool, extra: int) -> Path:
        path = self.base / f"cwebp-stub-{'grow' if grow else 'shrink'}-{extra}"
        path.write_text(
            STUB.format(python=sys.executable, log=str(self.log), grow=grow, extra=extra)
        )
        path.chmod(0o755)
        return path

    def add_asset(self, name: str, width: int = 1200, height: int = 800) -> Path:
        path = self.assets / name
        path.write_bytes(solid_png(width, height))
        return path

    def add_note(self, name: str, body: str) -> Path:
        path = self.folder / name
        path.write_text(body, encoding="utf-8")
        return path

    def run_optimizer(self, *extra: str, encoder: Path | None = None, expect: int = 0,
                      target: Path | None = None):
        command = [
            sys.executable, str(SCRIPT), str(target or self.folder),
            "--vault-root", str(self.vault),
            "--cwebp", str(encoder or self.encoder),
            *extra,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def argv(self) -> list[str]:
        return self.log.read_text().split()


class DeliveryPolicyTests(OptimizerTestCase):
    def test_converts_every_raster_and_rewrites_every_reference(self):
        self.add_asset("coding-stages.png", 2000, 1000)
        note = self.add_note(
            "week3-research.md",
            "# Week 3\n\n![[assets/coding-stages.png|420]]\n",
        )
        canvas = self.folder / "week3-research.canvas"
        canvas.write_text(
            json.dumps({"nodes": [{"type": "file", "file": "assets/coding-stages.png"}]}),
            encoding="utf-8",
        )
        ledger = self.base / "page-ledger.json"
        ledger.write_text(
            json.dumps({"pages": [{"page": 3, "visuals": [{"asset": "coding-stages.png"}]}]}),
            encoding="utf-8",
        )

        report = self.run_optimizer("--ledger", str(ledger))

        self.assertEqual([entry["asset"] for entry in report["converted"]], ["coding-stages.png"])
        self.assertEqual(report["converted"][0]["delivered_as"], "coding-stages.webp")
        self.assertTrue(report["converted"][0]["resized"])
        self.assertFalse((self.assets / "coding-stages.png").exists())
        self.assertTrue((self.assets / "coding-stages.webp").exists())
        self.assertIn("![[assets/coding-stages.webp|420]]", note.read_text(encoding="utf-8"))
        self.assertIn("assets/coding-stages.webp", canvas.read_text(encoding="utf-8"))
        self.assertIn(
            "coding-stages.webp",
            json.loads(ledger.read_text(encoding="utf-8"))["pages"][0]["visuals"][0]["asset"],
        )
        self.assertLess(report["bytes_after"], report["bytes_before"])

    def requested_resize(self) -> list[str]:
        argv = self.argv()
        return argv[argv.index("-resize") + 1:][:2] if "-resize" in argv else []

    def test_a_landscape_over_the_cap_is_bounded_by_width(self):
        self.add_asset("wide.png", 2000, 500)
        self.run_optimizer()
        self.assertEqual(self.requested_resize(), ["1600", "0"])

    def test_a_portrait_over_the_cap_is_bounded_by_height(self):
        self.add_asset("tall.png", 500, 2000)
        self.run_optimizer()
        self.assertEqual(self.requested_resize(), ["0", "1600"])

    def test_a_figure_within_the_cap_is_never_upscaled_or_downscaled(self):
        self.add_asset("small.png", 800, 600)
        report = self.run_optimizer()
        self.assertEqual(self.requested_resize(), [])
        self.assertFalse(report["converted"][0]["resized"])
        self.assertTrue((self.assets / "small.webp").exists())

    def test_a_delivered_webp_over_the_cap_is_re_encoded_onto_itself(self):
        oversized = self.assets / "legacy.webp"
        oversized.write_bytes(solid_png(2400, 1200))
        note = self.add_note("week3-research.md", "![[assets/legacy.webp|420]]\n")

        report = self.run_optimizer()

        self.assertEqual(
            [(entry["asset"], entry["delivered_as"]) for entry in report["converted"]],
            [("legacy.webp", "legacy.webp")],
        )
        self.assertTrue(oversized.is_file())
        self.assertIn("assets/legacy.webp", note.read_text(encoding="utf-8"))

    def test_webp_within_the_cap_is_left_alone(self):
        delivered = self.assets / "already.webp"
        delivered.write_bytes(solid_png(1200, 800))
        before = delivered.read_bytes()

        report = self.run_optimizer()

        self.assertEqual([entry["asset"] for entry in report["kept"]], ["already.webp"])
        self.assertEqual(delivered.read_bytes(), before)
        self.assertEqual(report["converted"], [])

    def test_a_file_is_never_replaced_by_a_larger_one(self):
        self.add_asset("flat.png", 400, 300)
        grower = self.write_encoder(grow=True, extra=4096)

        report = self.run_optimizer(encoder=grower)

        self.assertEqual(report["converted"], [])
        self.assertIn("would not be smaller", report["kept"][0]["reason"])
        self.assertTrue((self.assets / "flat.png").exists())
        self.assertFalse((self.assets / "flat.webp").exists())

    def test_force_delivers_a_uniform_folder_even_when_a_file_grows(self):
        self.add_asset("flat.png", 400, 300)
        grower = self.write_encoder(grow=True, extra=4096)

        report = self.run_optimizer("--force", encoder=grower)

        self.assertEqual(report["policy"]["force"], True)
        self.assertEqual([entry["asset"] for entry in report["converted"]], ["flat.png"])
        self.assertTrue(report["converted"][0]["forced"])
        self.assertFalse((self.assets / "flat.png").exists())
        self.assertTrue((self.assets / "flat.webp").exists())

    def test_an_existing_different_target_is_a_collision(self):
        self.add_asset("diagram.png")
        (self.assets / "diagram.webp").write_bytes(solid_png(64, 64))

        report = self.run_optimizer(expect=1)

        self.assertIn("collision", report["failed"][0]["reason"])
        self.assertTrue((self.assets / "diagram.png").exists())
        self.assertTrue((self.assets / "diagram.webp").exists())

    def test_an_identical_target_counts_as_already_delivered(self):
        self.add_asset("diagram.png")
        produced = self.base / "produced.webp"
        subprocess.run(
            [sys.executable, str(self.encoder), "-o", str(produced),
             str(self.assets / "diagram.png")],
            check=True,
        )
        (self.assets / "diagram.webp").write_bytes(produced.read_bytes())

        report = self.run_optimizer()

        self.assertEqual(report["converted"], [])
        self.assertEqual(
            sorted(entry["asset"] for entry in report["kept"]),
            ["diagram.png", "diagram.webp"],
        )
        self.assertTrue((self.assets / "diagram.png").exists())

    def test_an_unreadable_asset_fails_instead_of_silently_keeping_it(self):
        (self.assets / "broken.png").write_bytes(b"not an image at all")

        report = self.run_optimizer(expect=1)

        self.assertEqual(report["failed"][0]["asset"], "broken.png")
        self.assertTrue((self.assets / "broken.png").exists())

    def test_an_unusable_encoder_binary_is_reported(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), str(self.folder),
                "--vault-root", str(self.vault),
                "--cwebp", str(self.base / "absent"),
            ],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("not an executable file", result.stderr)

    def test_out_of_range_quality_is_a_usage_error(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), str(self.folder),
                "--vault-root", str(self.vault),
                "--cwebp", str(self.encoder), "--quality", "0",
            ],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("quality", result.stderr)

    def test_an_unreadable_vault_root_is_a_usage_error(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), str(self.folder),
                "--vault-root", str(self.base / "absent"),
                "--cwebp", str(self.encoder),
            ],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)

    def test_gif_and_svg_pass_through_untouched(self):
        animation = self.assets / "walkthrough.gif"
        animation.write_bytes(b"GIF89a" + bytes(32))
        vector = self.assets / "curve.svg"
        vector.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")

        report = self.run_optimizer()

        self.assertEqual(sorted(report["passthrough"]), ["curve.svg", "walkthrough.gif"])
        self.assertTrue(animation.exists() and vector.exists())
        self.assertFalse((self.assets / "walkthrough.webp").exists())

    def test_dry_run_reports_the_plan_and_changes_nothing(self):
        self.add_asset("coding-stages.png", 2000, 1000)
        note = self.add_note("week3-research.md", "![[assets/coding-stages.png|420]]\n")

        report = self.run_optimizer("--dry-run")

        self.assertEqual(len(report["converted"]), 1)
        self.assertTrue(report["policy"]["dry_run"])
        self.assertTrue((self.assets / "coding-stages.png").exists())
        self.assertFalse((self.assets / "coding-stages.webp").exists())
        self.assertIn("coding-stages.png", note.read_text(encoding="utf-8"))
        self.assertEqual(report["rewritten_files"], [])

    def test_a_leftover_reference_retains_the_original(self):
        self.add_asset("matrix.png")
        second = self.vault / "COURSE101/Lectures/week1-basics"
        (second / "assets").mkdir(parents=True)
        (second / "assets" / "matrix.png").write_bytes(solid_png(300, 200))
        self.add_note("week3-research.md", "![[assets/matrix.png|420]]\n")
        (self.vault / "index.md").write_text("![[assets/matrix.png|420]]\n", encoding="utf-8")

        report = self.run_optimizer("--all-assets", target=self.vault)

        self.assertTrue((self.assets / "matrix.png").exists())
        self.assertTrue((second / "assets" / "matrix.png").exists())
        retained = report["retained_originals"]
        self.assertEqual(retained[0]["asset"], "matrix.png")
        self.assertEqual(sorted(retained[0]["still_referenced_by"]), ["index.md"])
        self.assertTrue(report["warnings"])
        self.assertIn(
            "assets/matrix.webp",
            (self.folder / "week3-research.md").read_text(encoding="utf-8"),
        )

    def test_same_name_in_two_courses_never_crosses_the_wire(self):
        self.add_asset("matrix.png")
        second = self.vault / "COURSE101/Lectures/week1-basics"
        (second / "assets").mkdir(parents=True)
        (second / "assets" / "matrix.png").write_bytes(solid_png(300, 200))
        first_note = self.add_note("week3-research.md", "![[assets/matrix.png|420]]\n")
        second_note = second / "week1-basics.md"
        second_note.write_text("![[assets/matrix.png|420]]\n", encoding="utf-8")

        self.run_optimizer("--all-assets", target=self.vault)

        self.assertIn("assets/matrix.webp", first_note.read_text(encoding="utf-8"))
        self.assertIn("assets/matrix.webp", second_note.read_text(encoding="utf-8"))
        self.assertFalse((self.assets / "matrix.png").exists())
        self.assertFalse((second / "assets" / "matrix.png").exists())
        self.assertEqual(self.run_optimizer(target=self.vault, *["--all-assets"])["converted"], [])

    def test_all_assets_sweeps_every_document_folder(self):
        self.add_asset("coding-stages.png")
        second = self.vault / "COURSE101/Lectures/week1-basics"
        (second / "assets").mkdir(parents=True)
        (second / "assets" / "taxonomy.png").write_bytes(solid_png(1900, 1200))

        report = self.run_optimizer("--all-assets", target=self.vault)

        self.assertEqual(len(report["converted"]), 2)
        self.assertTrue((self.assets / "coding-stages.webp").exists())
        self.assertTrue((second / "assets" / "taxonomy.webp").exists())


@unittest.skipUnless(shutil.which("cwebp"), "cwebp is not installed")
class RealEncoderTests(OptimizerTestCase):
    def test_the_real_encoder_delivers_a_valid_bounded_webp(self):
        encoder = shutil.which("cwebp")
        source = self.add_asset("full-page-render.png", 2400, 1500)
        self.add_note("week3-research.md", "![[assets/full-page-render.png|420]]\n")

        report = self.run_optimizer(encoder=encoder)

        delivered = self.assets / "full-page-render.webp"
        self.assertTrue(delivered.is_file())
        self.assertFalse(source.exists())
        data = delivered.read_bytes()
        self.assertEqual(data[:4], b"RIFF")
        self.assertEqual(data[8:12], b"WEBP")
        width, height = self.dimensions(data)
        self.assertEqual(max(width, height), 1600)
        self.assertLess(report["bytes_after"], report["bytes_before"] // 4)
        self.assertIn(
            "assets/full-page-render.webp",
            (self.folder / "week3-research.md").read_text(encoding="utf-8"),
        )

    def dimensions(self, data: bytes) -> tuple[int, int]:
        start = data.find(b"VP8 ")
        if start > 0:
            return (
                int.from_bytes(data[start + 14:start + 16], "little") & 0x3FFF,
                int.from_bytes(data[start + 16:start + 18], "little") & 0x3FFF,
            )
        start = data.find(b"VP8L")
        if start > 0:
            bits = int.from_bytes(data[start + 9:start + 13], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        start = data.find(b"VP8X")
        return (
            int.from_bytes(data[start + 12:start + 15], "little") + 1,
            int.from_bytes(data[start + 15:start + 18], "little") + 1,
        )


if __name__ == "__main__":
    unittest.main()
