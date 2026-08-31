import importlib.util
import json
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/lecture-slides-to-obsidian/scripts/mineru-cli-adapter.py"
SPEC = importlib.util.spec_from_file_location("mineru_cli_adapter", SCRIPT)
ADAPTER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ADAPTER)


class MineruCliAdapterTests(unittest.TestCase):
    def make_fake_cli(self, base: Path) -> Path:
        executable = base / "mineru-open-api"
        executable.write_text(
            "#!/usr/bin/env python3\n" + textwrap.dedent(
                """
                import json
                import os
                import pathlib
                import sys

                assert sys.argv[1] == "extract"
                assert "--token" not in sys.argv
                token = os.environ["MINERU_TOKEN"]
                output = pathlib.Path(sys.argv[sys.argv.index("-o") + 1])
                source = pathlib.Path(sys.argv[2])
                output.mkdir(parents=True, exist_ok=True)
                (output / f"{source.stem}.md").write_text("# Extracted\\n")
                (output / "images").mkdir()
                (output / "images" / "figure.png").write_bytes(b"synthetic")
                content = [
                    {"type":"text","text":"Section","text_level":1,"page_idx":0,"bbox":[0,0,10,10]},
                    {"type":"text","text":"Body","page_idx":0},
                    {"type":"image","img_path":"images/figure.png","page_idx":1},
                    {"type":"page_footnote","text":"Repeated footer","page_idx":1}
                ]
                (output / f"{source.stem}.json").write_text(json.dumps(content))
                print(f"debug token={token}", file=sys.stderr)
                """
            )
        )
        executable.chmod(0o755)
        return executable

    def test_official_cli_wrapper_and_legacy_normalization(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "example.pdf"
            source.write_bytes(b"synthetic")
            executable = self.make_fake_cli(base)
            token = "synthetic-token-value"
            result = ADAPTER.run_extract(
                source,
                base / "output",
                token,
                "en",
                False,
                executable=str(executable),
            )
            self.assertEqual(result["page_count"], 2)
            self.assertNotIn(token, result["stderr"])
            self.assertIn("[REDACTED]", result["stderr"])
            pages = json.loads(Path(result["normalized_page_groups"]).read_text())
            self.assertEqual(pages[0][0]["type"], "title")
            self.assertEqual(pages[0][1]["type"], "paragraph")
            self.assertEqual(pages[1][0]["type"], "image")
            self.assertEqual(pages[1][1]["type"], "page_footnote")
            self.assertEqual(
                pages[1][0]["content"]["img_path"],
                "normalized-assets/page-002-figure-01.png",
            )
            self.assertEqual(result["asset_candidates"], ["images/figure.png"])
            self.assertTrue(Path(result["normalized_assets_dir"]).is_dir())
            self.assertTrue(Path(result["normalized_assets"][0]).is_file())
            self.assertEqual(Path(result["normalized_assets"][0]).name, "page-002-figure-01.png")
            asset_map = json.loads(Path(result["asset_map"]).read_text())
            self.assertEqual(asset_map[0]["final_name"], "page-002-figure-01.png")

    def test_missing_page_idx_is_rejected(self):
        with self.assertRaises(ADAPTER.AdapterError):
            ADAPTER.legacy_content_list_to_pages([{"type": "text", "text": "Body"}])

    def test_asset_names_increment_per_page_and_kind(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            images = output / "images"
            images.mkdir()
            for name in ("a.png", "b.JPG", "table.png"):
                (images / name).write_bytes(name.encode())
            legacy = [
                {"type": "image", "img_path": "images/a.png", "page_idx": 0},
                {"type": "image", "img_path": "images/b.JPG", "page_idx": 0},
                {"type": "table", "img_path": "images/table.png", "page_idx": 0},
            ]
            pages = ADAPTER.legacy_content_list_to_pages(legacy)
            _, asset_map, files, _ = ADAPTER.normalize_referenced_assets(legacy, output, pages)
            self.assertEqual(
                [item["final_name"] for item in asset_map],
                [
                    "page-001-figure-01.png",
                    "page-001-figure-02.jpg",
                    "page-001-table-01.png",
                ],
            )
            self.assertTrue(all(Path(path).is_file() for path in files))

    def test_visual_type_mapping(self):
        self.assertEqual(ADAPTER.asset_kind({"type": "image"}), "figure")
        self.assertEqual(ADAPTER.asset_kind({"type": "image", "sub_type": "chart"}), "chart")
        self.assertEqual(ADAPTER.asset_kind({"type": "chart"}), "chart")
        self.assertEqual(ADAPTER.asset_kind({"type": "table"}), "table")
        self.assertEqual(ADAPTER.asset_kind({"type": "equation"}), "equation")


if __name__ == "__main__":
    unittest.main()
