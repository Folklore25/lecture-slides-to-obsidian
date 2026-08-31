#!/usr/bin/env python3
"""Build a deterministic relationship Canvas from one complete Markdown note."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path


PROFILES = ("lecture-notes", "policy-document", "paper")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}


class CanvasBuildError(RuntimeError):
    pass


def inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def stable_id(kind: str, value: str) -> str:
    return hashlib.blake2b(f"{kind}\0{value}".encode("utf-8"), digest_size=8).hexdigest()


def parse_headings(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    h1 = re.search(r"(?m)^#\s+(.+?)\s*$", markdown)
    title = h1.group(1) if h1 else "Course material"
    headings: list[tuple[str, str]] = []
    for match in re.finditer(r"(?m)^(##|###)\s+(.+?)\s*$", markdown):
        headings.append((match.group(1), match.group(2)))
    return title, headings


def build_canvas(note: Path, vault_root: Path, profile: str, assets_dir: Path | None = None) -> dict:
    note = note.resolve()
    vault_root = vault_root.resolve()
    if not note.is_file() or not inside(note, vault_root):
        raise CanvasBuildError("note must be an existing file inside vault_root")
    note_relative = note.relative_to(vault_root).as_posix()
    document_folder = note.parent
    title, headings = parse_headings(note.read_text(encoding="utf-8"))

    central_id = stable_id("file", note_relative)
    profile_id = stable_id("profile", profile)
    nodes = [
        {
            "id": profile_id,
            "type": "text",
            "x": 0,
            "y": -180,
            "width": 420,
            "height": 120,
            "text": f"# {profile}\n\n{title}",
            "color": "6",
        },
        {
            "id": central_id,
            "type": "file",
            "x": 0,
            "y": 0,
            "width": 420,
            "height": 320,
            "file": note_relative,
            "color": "1",
        },
    ]
    edges = []
    previous_section = None
    for index, (_, heading) in enumerate(headings[:12]):
        node_id = stable_id("section", f"{note_relative}#{index}:{heading}")
        x = 520 + (index % 2) * 460
        y = (index // 2) * 280
        nodes.append(
            {
                "id": node_id,
                "type": "file",
                "x": x,
                "y": y,
                "width": 380,
                "height": 220,
                "file": note_relative,
                "subpath": f"#{heading}",
            }
        )
        edges.append(
            {
                "id": stable_id("edge", f"{central_id}->{node_id}"),
                "fromNode": central_id,
                "fromSide": "right",
                "toNode": node_id,
                "toSide": "left",
                "toEnd": "arrow",
                "label": "contains section",
            }
        )
        if previous_section:
            edges.append(
                {
                    "id": stable_id("edge", f"{previous_section}->{node_id}"),
                    "fromNode": previous_section,
                    "fromSide": "bottom",
                    "toNode": node_id,
                    "toSide": "top",
                    "toEnd": "arrow",
                    "label": "followed by",
                }
            )
        previous_section = node_id

    assets_dir = assets_dir.resolve() if assets_dir else document_folder / "assets"
    if assets_dir.exists():
        if not inside(assets_dir, document_folder):
            raise CanvasBuildError("assets directory must remain inside the document folder")
        asset_files = sorted(
            path for path in assets_dir.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )[:12]
        for index, asset in enumerate(asset_files):
            relative = asset.relative_to(vault_root).as_posix()
            node_id = stable_id("asset", relative)
            nodes.append(
                {
                    "id": node_id,
                    "type": "file",
                    "x": 1500,
                    "y": index * 260,
                    "width": 380,
                    "height": 220,
                    "file": relative,
                    "color": "5",
                }
            )
            edges.append(
                {
                    "id": stable_id("edge", f"{central_id}->{node_id}"),
                    "fromNode": central_id,
                    "fromSide": "right",
                    "toNode": node_id,
                    "toSide": "left",
                    "toEnd": "arrow",
                    "label": "includes asset",
                }
            )
    return {"nodes": nodes, "edges": edges}


def write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--note", required=True, type=Path)
    parser.add_argument("--vault-root", required=True, type=Path)
    parser.add_argument("--profile", required=True, choices=PROFILES)
    parser.add_argument("--assets-dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        canvas = build_canvas(args.note, args.vault_root, args.profile, args.assets_dir)
        if args.output.resolve().parent != args.note.resolve().parent:
            raise CanvasBuildError("Canvas output must be beside the complete Markdown note")
        write_atomic(args.output, canvas)
    except (OSError, CanvasBuildError) as exc:
        print(f"build-canvas error: {exc}", file=sys.stderr)
        return 1
    print(f"relationship Canvas written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
