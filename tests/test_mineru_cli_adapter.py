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
            self.assertEqual(result["asset_candidates"], ["images/figure.png"])
            self.assertTrue(Path(result["normalized_assets_dir"]).is_dir())
            self.assertTrue(Path(result["normalized_assets"][0]).is_file())

    def test_missing_page_idx_is_rejected(self):
        with self.assertRaises(ADAPTER.AdapterError):
            ADAPTER.legacy_content_list_to_pages([{"type": "text", "text": "Body"}])


if __name__ == "__main__":
    unittest.main()
