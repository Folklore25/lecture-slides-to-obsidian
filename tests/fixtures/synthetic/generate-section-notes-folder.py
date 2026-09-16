#!/usr/bin/env python3
"""Regenerate the derived artifacts of the section-notes-folder synthetic fixture.

Hand-authored inputs (committed as-is):
  week3-qualitative-research.md
  ../staging/note-plan.json, page-ledger.json, page-groups.json

Generated outputs:
  week3-qualitative-research.canvas   built by the real recall-model -> Canvas renderer
  assets/qualitative-research-cycle.png  a deterministic 8x8 PNG placeholder

The Canvas is built inside a throwaway vault so the real script's path checks run, then its
vault-relative file nodes are rewritten to document-relative ones for `--fixture-mode`.
"""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path


FIXTURE = Path(__file__).resolve().parent / "section-notes-folder"
REPO = Path(__file__).resolve().parents[3]
CANVAS_SKILL = REPO / "skills/obsidian-canvas-designer"
NOTE_NAME = "week3-qualitative-research"
ASSET_NAME = "qualitative-research-cycle.png"
VAULT_PREFIX = "COURSE101/Lectures/week3/"


def png_bytes(width: int = 8, height: int = 8) -> bytes:
    raw = b"".join(b"\x00" + bytes([30, 90, 160] * width) for _ in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def main() -> int:
    note = FIXTURE / f"{NOTE_NAME}.md"
    model = CANVAS_SKILL / "templates/recall-model.content-driven.example.json"
    for required in (note, model):
        if not required.is_file():
            print(f"missing required input: {required}", file=sys.stderr)
            return 1

    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        vault = base / "vault"
        document = vault / VAULT_PREFIX
        (document / "assets").mkdir(parents=True)
        shutil.copy2(note, document / f"{NOTE_NAME}.md")
        (document / "assets" / ASSET_NAME).write_bytes(png_bytes())

        canvas_path = document / f"{NOTE_NAME}.canvas"
        built = subprocess.run(
            [
                sys.executable, str(CANVAS_SKILL / "scripts/build-canvas.py"),
                "--note", str(document / f"{NOTE_NAME}.md"),
                "--vault-root", str(vault),
                "--profile", "lecture-notes",
                "--model", str(model),
                "--output", str(canvas_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if built.returncode != 0:
            print(built.stdout[-4000:], file=sys.stderr)
            print(built.stderr[-4000:], file=sys.stderr)
            return 1

        data = json.loads(canvas_path.read_text(encoding="utf-8"))
        for node in data["nodes"]:
            if node.get("type") == "file" and node["file"].startswith(VAULT_PREFIX):
                node["file"] = node["file"][len(VAULT_PREFIX) :]

        (FIXTURE / f"{NOTE_NAME}.canvas").write_text(
            json.dumps(data, ensure_ascii=False, indent="\t") + "\n", encoding="utf-8"
        )
        (FIXTURE / "assets").mkdir(exist_ok=True)
        (FIXTURE / "assets" / ASSET_NAME).write_bytes(png_bytes())

    print(f"regenerated {NOTE_NAME}.canvas and assets/{ASSET_NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
