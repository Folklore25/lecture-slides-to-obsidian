#!/usr/bin/env python3
"""Validate one derived Obsidian course-document folder using only stdlib."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SOURCE_EXTENSIONS = {
    ".pdf", ".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".7z", ".rar", ".tar", ".gz",
}
REQUIRED_PROPERTIES = {
    "type", "course", "title", "source_filename", "source_format",
    "source_sha256", "source_pages", "conversion_profile",
    "mineru_model", "status",
}
PROFILES = {"lecture-notes", "policy-document", "paper"}
REPORT_SECTIONS = {
    "Matched routing", "Pipeline", "Outputs", "Content inventory",
    "Quality gates", "Review items", "Not checked",
}
INVENTORY_LABELS = {
    "Figures/images", "Tables", "Equations", "Fallback pages",
    "Page headers", "Page footers", "Page footnotes",
}
HEX_ID = re.compile(r"^[0-9a-f]{16}$")
MARKER = re.compile(r"<!--\s*source-page:\s*(\d+)\s*-->")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if match:
            data[match.group(1)] = match.group(2).strip('"\'')
    return data, text[end + 5 :]


def inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def local_target(raw: str) -> str | None:
    target = raw.strip().strip("<>").split("#", 1)[0]
    if not target or re.match(r"^(?:https?:|data:|mailto:)", target):
        return None
    return target


def validate_markdown(path: Path, folder: Path, vault_root: Path | None) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    props, body = parse_frontmatter(text)
    missing = sorted(REQUIRED_PROPERTIES - props.keys())
    if missing:
        errors.append(f"markdown missing properties: {', '.join(missing)}")
    if props.get("type") != "course-material":
        errors.append("frontmatter type must be course-material")
    source_filename = props.get("source_filename", "")
    if not source_filename or Path(source_filename).name != source_filename:
        errors.append("source_filename must be a basename, not a path")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", props.get("source_sha256", "")):
        errors.append("source_sha256 must contain 64 hexadecimal characters")

    try:
        page_count = int(props.get("source_pages", "0"))
    except ValueError:
        page_count = 0
    if page_count <= 0:
        errors.append("source_pages must be a positive integer")

    profile = props.get("conversion_profile")
    if profile not in PROFILES:
        errors.append(f"invalid conversion_profile: {profile!r}")

    h1_count = len(re.findall(r"(?m)^#\s+\S", body))
    if h1_count != 1:
        errors.append(f"expected exactly one H1, found {h1_count}")

    markers = [int(value) for value in MARKER.findall(body)]
    if not markers:
        errors.append("no source-page markers found")
    if markers != sorted(markers):
        errors.append("source-page markers are not monotonic")
    invalid = [value for value in markers if value < 1 or value > page_count]
    if invalid:
        errors.append(f"source-page markers outside 1..{page_count}: {invalid}")

    targets: list[str] = []
    targets += re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body)
    targets += re.findall(r"!\[\[([^\]|#]+)", body)
    for raw in targets:
        target = local_target(raw)
        if target is None:
            continue
        candidate = (folder / target).resolve()
        if not inside(candidate, folder) or not candidate.is_file():
            errors.append(f"unresolved or escaping asset/embed: {target}")

    if vault_root:
        for raw in re.findall(r"(?<!!)\[\[([^\]|#]+)", body):
            target = local_target(raw)
            if target is None:
                continue
            candidate = vault_root / target
            candidates = [candidate] if candidate.suffix else [candidate.with_suffix(".md")]
            if not any(item.is_file() for item in candidates):
                by_name = list(vault_root.rglob(Path(target).name + ".md")) if not candidate.suffix else []
                if len(by_name) != 1:
                    errors.append(f"unresolved or ambiguous wikilink: {target}")

    return errors


def rectangles_overlap(a: dict, b: dict) -> bool:
    if a.get("type") == "group" or b.get("type") == "group":
        return False
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


def validate_canvas(path: Path, folder: Path, vault_root: Path | None) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"invalid canvas JSON: {exc}"]

    nodes = data.get("nodes")
    edges = data.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return ["canvas must contain nodes and edges arrays"]

    all_ids: list[str] = []
    node_ids: set[str] = set()
    valid_nodes: list[dict] = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"node {index} is not an object")
            continue
        node_id = node.get("id", "")
        all_ids.append(node_id)
        node_ids.add(node_id)
        if not HEX_ID.fullmatch(node_id):
            errors.append(f"invalid node id: {node_id!r}")
        node_type = node.get("type")
        if node_type not in {"text", "file", "link", "group"}:
            errors.append(f"invalid node type for {node_id}: {node_type!r}")
        for field in ("x", "y", "width", "height"):
            if not isinstance(node.get(field), (int, float)):
                errors.append(f"node {node_id} missing numeric {field}")
        if node_type == "text" and not isinstance(node.get("text"), str):
            errors.append(f"text node {node_id} missing text")
        if node_type == "file":
            raw_file = node.get("file")
            if not isinstance(raw_file, str) or not raw_file:
                errors.append(f"file node {node_id} missing file")
            else:
                file_path = Path(raw_file)
                if file_path.is_absolute() or ".." in file_path.parts:
                    errors.append(f"file node escapes vault/document folder: {raw_file}")
                if file_path.suffix.lower() in SOURCE_EXTENSIONS:
                    errors.append(f"file node targets forbidden source original: {raw_file}")
                if vault_root:
                    resolved = (vault_root / file_path).resolve()
                    if not resolved.is_file() or not inside(resolved, folder):
                        errors.append(f"file node unresolved/outside document folder: {raw_file}")
                elif len(file_path.parts) == 1 or file_path.parts[0] == "assets":
                    resolved = (folder / file_path).resolve()
                    if not resolved.is_file() or not inside(resolved, folder):
                        errors.append(f"file node unresolved: {raw_file}")
                else:
                    errors.append(f"vault-relative file node requires --vault-root: {raw_file}")
        if all(isinstance(node.get(field), (int, float)) for field in ("x", "y", "width", "height")):
            valid_nodes.append(node)

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edge {index} is not an object")
            continue
        edge_id = edge.get("id", "")
        all_ids.append(edge_id)
        if not HEX_ID.fullmatch(edge_id):
            errors.append(f"invalid edge id: {edge_id!r}")
        for field in ("fromNode", "toNode"):
            if edge.get(field) not in node_ids:
                errors.append(f"edge {edge_id} has dangling {field}: {edge.get(field)!r}")

    if len(all_ids) != len(set(all_ids)):
        errors.append("canvas IDs are not unique across nodes and edges")

    for index, first in enumerate(valid_nodes):
        for second in valid_nodes[index + 1 :]:
            if rectangles_overlap(first, second):
                errors.append(f"canvas nodes overlap: {first.get('id')} and {second.get('id')}")

    return errors


def validate_report(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    sections = set(re.findall(r"(?m)^##\s+(.+?)\s*$", text))
    missing = sorted(REPORT_SECTIONS - sections)
    if missing:
        errors.append(f"report missing sections: {', '.join(missing)}")
    for label in sorted(INVENTORY_LABELS):
        if not re.search(rf"(?m)^\|\s*{re.escape(label)}\s*\|\s*\d+\s*\|", text):
            errors.append(f"report missing numeric inventory row: {label}")
    if "Pixel-level visual diff" not in text or "NOT-CHECKED" not in text:
        errors.append("report must mark pixel-level visual diff as NOT-CHECKED when unperformed")
    secret_patterns = [
        r"Authorization:\s*Bearer\s+\S+",
        r"https?://\S+\?\S+",
        r"/Users/[^\s|]+",
        r"/home/[^\s|]+",
    ]
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in secret_patterns):
        errors.append("report contains a secret URL/header or absolute source path")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_folder", type=Path)
    parser.add_argument("--vault-root", type=Path)
    args = parser.parse_args()

    folder = args.document_folder.resolve()
    vault_root = args.vault_root.resolve() if args.vault_root else None
    errors: list[str] = []

    if not folder.is_dir():
        errors.append(f"document folder not found: {folder}")
    elif vault_root and not inside(folder, vault_root):
        errors.append("document folder is outside --vault-root")

    if not errors:
        forbidden = [path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS]
        if forbidden:
            errors.append("source originals found in document folder: " + ", ".join(path.name for path in forbidden))

        markdown_files = [path for path in folder.glob("*.md") if path.name != "conversion-report.md"]
        canvas_files = list(folder.glob("*.canvas"))
        report = folder / "conversion-report.md"
        assets = folder / "assets"
        if len(markdown_files) != 1:
            errors.append(f"expected one primary Markdown file, found {len(markdown_files)}")
        if len(canvas_files) != 1:
            errors.append(f"expected one Canvas file, found {len(canvas_files)}")
        if not report.is_file():
            errors.append("conversion-report.md is missing")
        if not assets.is_dir():
            errors.append("assets directory is missing")

        if len(markdown_files) == 1:
            errors += validate_markdown(markdown_files[0], folder, vault_root)
        if len(canvas_files) == 1:
            errors += validate_canvas(canvas_files[0], folder, vault_root)
        if report.is_file():
            errors += validate_report(report)

    result = {"valid": not errors, "document_folder": str(folder), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
