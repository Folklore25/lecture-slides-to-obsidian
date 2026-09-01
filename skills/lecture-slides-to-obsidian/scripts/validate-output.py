#!/usr/bin/env python3
"""Validate one derived Obsidian course-document folder using only stdlib."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SOURCE_EXTENSIONS = {
    ".pdf", ".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".7z", ".rar", ".tar", ".gz",
}
VISUAL_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}
ASSET_NAME = re.compile(
    r"^page-(\d{3})-(figure|table|equation|chart|fallback)-(\d{2})\.[a-z0-9]+$"
)
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
RECALL_ROLE = re.compile(r"<!--\s*recall-map:\s*([a-z-]+)\s*-->")
BANNED_CANVAS_EDGE_LABELS = {
    "related to", "contains", "contains section", "followed by", "includes asset",
    "connects to", "next", "section",
}


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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

    note_candidates = [item for item in folder.glob("*.md") if item.name != "conversion-report.md"]
    note_h2: set[str] = set()
    note_h2_pages: dict[str, set[int]] = {}
    note_page_count = 0
    if len(note_candidates) == 1:
        note_text = note_candidates[0].read_text(encoding="utf-8")
        note_h2 = set(re.findall(r"(?m)^##\s+(.+?)\s*$", note_text))
        current_page: int | None = None
        for line in note_text.splitlines():
            marker = re.fullmatch(r"<!--\s*source-page:\s*(\d+)\s*-->", line.strip())
            if marker:
                current_page = int(marker.group(1))
                continue
            heading = re.fullmatch(r"##\s+(.+?)\s*", line)
            if heading and current_page is not None:
                note_h2_pages.setdefault(heading.group(1).strip(), set()).add(current_page)
        note_props, _ = parse_frontmatter(note_text)
        try:
            note_page_count = int(note_props.get("source_pages", "0"))
        except ValueError:
            note_page_count = 0

    all_ids: list[str] = []
    node_ids: set[str] = set()
    valid_nodes: list[dict] = []
    role_nodes: dict[str, list[str]] = {}
    group_count = 0
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
        if node_type == "text":
            text = node.get("text")
            if not isinstance(text, str):
                errors.append(f"text node {node_id} missing text")
            else:
                role_match = RECALL_ROLE.search(text)
                if role_match:
                    role_nodes.setdefault(role_match.group(1), []).append(node_id)
                if any(marker in text for marker in ("[Populate", "[Replace", "TODO")):
                    errors.append(f"text node {node_id} contains a placeholder")
                if len(text) > 1400:
                    errors.append(f"text node {node_id} is too dense for recall: {len(text)} characters")
                if role_match and role_match.group(1) == "concept":
                    source_link = re.search(r"\[\[[^\]]+#([^\]|]+)\|Source p\.(\d+)\]\]", text)
                    if not source_link:
                        errors.append(f"concept node {node_id} is missing a compact source-heading/page link")
                    elif source_link.group(1) not in note_h2:
                        errors.append(f"concept node {node_id} links an unknown source heading: {source_link.group(1)}")
                    source_page = int(source_link.group(2)) if source_link else None
                    if source_page is not None and not 1 <= source_page <= note_page_count:
                        errors.append(f"concept node {node_id} source page is outside 1..{note_page_count}")
                    elif source_link and source_link.group(1) in note_h2_pages and source_page not in note_h2_pages[source_link.group(1)]:
                        errors.append(
                            f"concept node {node_id} source heading/page pair does not occur in the note"
                        )
        if node_type == "group":
            group_count += 1
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
        label = edge.get("label")
        if not isinstance(label, str) or not label.strip():
            errors.append(f"edge {edge_id} is missing a meaningful label")
        elif len(label.strip()) > 48:
            errors.append(f"edge {edge_id} label is too long for scanning")
        elif label.strip().casefold() in BANNED_CANVAS_EDGE_LABELS:
            errors.append(f"edge {edge_id} uses a structural/generic label: {label!r}")
        for field in ("fromSide", "toSide"):
            if edge.get(field) not in {"top", "right", "bottom", "left"}:
                errors.append(f"edge {edge_id} has invalid {field}: {edge.get(field)!r}")
        if edge.get("toEnd", "arrow") not in {"none", "arrow"}:
            errors.append(f"edge {edge_id} has invalid toEnd: {edge.get('toEnd')!r}")

    if len(all_ids) != len(set(all_ids)):
        errors.append("canvas IDs are not unique across nodes and edges")

    for index, first in enumerate(valid_nodes):
        for second in valid_nodes[index + 1 :]:
            if rectangles_overlap(first, second):
                errors.append(f"canvas nodes overlap: {first.get('id')} and {second.get('id')}")

    for role in ("overview", "synthesis", "distinctions", "prompts"):
        if len(role_nodes.get(role, [])) != 1:
            errors.append(f"knowledge-recall Canvas requires exactly one {role} node")
    concept_ids = set(role_nodes.get("concept", []))
    if not 4 <= len(concept_ids) <= 20:
        errors.append(f"knowledge-recall Canvas requires 4..20 concept nodes, found {len(concept_ids)}")
    if not 2 <= group_count <= 7:
        errors.append(f"knowledge-recall Canvas requires 2..7 learning-module groups, found {group_count}")
    overview_ids = role_nodes.get("overview", [])
    if overview_ids:
        overview = next(node for node in nodes if node.get("id") == overview_ids[0])
        overview_text = overview.get("text", "")
        for phrase in ("# One-minute recall", "**Central question:**", "**Answer:**", "**Takeaways**"):
            if phrase not in overview_text:
                errors.append(f"overview node is missing {phrase}")

    semantic_edges = [
        edge for edge in edges
        if edge.get("fromNode") in concept_ids and edge.get("toNode") in concept_ids
    ]
    if concept_ids and not len(concept_ids) - 1 <= len(semantic_edges) <= len(concept_ids) * 2:
        errors.append("concept relations must stay between N-1 and 2N edges")
    adjacency = {node_id: set() for node_id in concept_ids}
    for edge in semantic_edges:
        source = edge.get("fromNode")
        target = edge.get("toNode")
        adjacency[source].add(target)
        adjacency[target].add(source)
    if adjacency:
        visited: set[str] = set()
        stack = [next(iter(adjacency))]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            stack.extend(adjacency[current] - visited)
        if visited != concept_ids:
            errors.append("concept relation graph is disconnected")
        crowded = sorted(node_id for node_id, neighbours in adjacency.items() if len(neighbours) > 6)
        if crowded:
            errors.append(f"concept nodes exceed six semantic connections: {', '.join(crowded)}")

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


def validate_assets(assets: Path, markdown_path: Path) -> list[str]:
    errors: list[str] = []
    props, _ = parse_frontmatter(markdown_path.read_text(encoding="utf-8"))
    try:
        page_count = int(props.get("source_pages", "0"))
    except ValueError:
        page_count = 0
    sequences: dict[tuple[int, str], list[int]] = {}
    for path in assets.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in VISUAL_EXTENSIONS:
            continue
        if path.parent != assets:
            errors.append(f"visual asset must be a flat file directly under assets/: {path.relative_to(assets)}")
            continue
        match = ASSET_NAME.fullmatch(path.name)
        if not match:
            errors.append(f"visual asset filename violates page-PPP-kind-NN.ext: {path.name}")
            continue
        page = int(match.group(1))
        kind = match.group(2)
        index = int(match.group(3))
        if page < 1 or page > page_count:
            errors.append(f"asset page outside 1..{page_count}: {path.name}")
        sequences.setdefault((page, kind), []).append(index)
    for (page, kind), values in sequences.items():
        ordered = sorted(values)
        expected = list(range(1, len(ordered) + 1))
        if ordered != expected:
            errors.append(
                f"asset sequence for page {page:03d} {kind} must be contiguous from 01: {ordered}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_folder", type=Path)
    parser.add_argument("--vault-root", type=Path)
    parser.add_argument("--fixture-mode", action="store_true", help="Allow document-relative Canvas paths in tests only")
    parser.add_argument("--report", required=True, type=Path, help="Temporary QA report outside the vault")
    parser.add_argument("--recall-model", type=Path, help="Temporary Agent-authored recall model outside the vault")
    parser.add_argument("--aesthetic-check", type=Path, help="Static Canvas aesthetic check outside the vault")
    parser.add_argument("--render-metrics", type=Path, help="First-pass Obsidian DOM measurements outside the vault")
    parser.add_argument("--render-check", type=Path, help="Final Obsidian DOM readability check outside the vault")
    parser.add_argument(
        "--delete-qa-on-success", "--delete-report-on-success",
        dest="delete_qa_on_success", action="store_true",
        help="Delete the report and supplied recall model after every check passes",
    )
    args = parser.parse_args()

    folder = args.document_folder.resolve()
    vault_root = args.vault_root.resolve() if args.vault_root else None
    report_input = args.report
    report = report_input.resolve()
    recall_model_input = args.recall_model
    recall_model = recall_model_input.resolve() if recall_model_input else None
    aesthetic_check_input = args.aesthetic_check
    aesthetic_check = aesthetic_check_input.resolve() if aesthetic_check_input else None
    render_metrics_input = args.render_metrics
    render_metrics = render_metrics_input.resolve() if render_metrics_input else None
    render_check_input = args.render_check
    render_check = render_check_input.resolve() if render_check_input else None
    render_metrics_data: dict | None = None
    render_check_data: dict | None = None
    aesthetic_check_data: dict | None = None
    errors: list[str] = []

    if vault_root is None and not args.fixture_mode:
        errors.append("--vault-root is required outside explicit --fixture-mode")
    if vault_root is not None and args.fixture_mode:
        errors.append("--fixture-mode cannot be combined with --vault-root")
    if report_input.is_symlink():
        errors.append("temporary conversion report must not be a symlink")
    if report.name != "conversion-report.md":
        errors.append("temporary report filename must be conversion-report.md")
    if vault_root is not None and recall_model is None:
        errors.append("--recall-model is required outside explicit --fixture-mode")
    if vault_root is not None and aesthetic_check is None:
        errors.append("--aesthetic-check is required outside explicit --fixture-mode")
    if vault_root is not None and render_metrics is None:
        errors.append("--render-metrics is required outside explicit --fixture-mode")
    if vault_root is not None and render_check is None:
        errors.append("--render-check is required outside explicit --fixture-mode")
    if recall_model_input is not None and recall_model_input.is_symlink():
        errors.append("temporary recall model must not be a symlink")
    if recall_model is not None and recall_model.name != "recall-model.json":
        errors.append("temporary recall model filename must be recall-model.json")
    if aesthetic_check_input is not None and aesthetic_check_input.is_symlink():
        errors.append("temporary aesthetic check must not be a symlink")
    if aesthetic_check is not None and aesthetic_check.name != "canvas-aesthetic-check.json":
        errors.append("temporary aesthetic check filename must be canvas-aesthetic-check.json")
    for input_path, resolved, expected_name, label in (
        (render_metrics_input, render_metrics, "canvas-render-metrics.json", "render metrics"),
        (render_check_input, render_check, "canvas-render-check.json", "render check"),
    ):
        if input_path is not None and input_path.is_symlink():
            errors.append(f"temporary {label} must not be a symlink")
        if resolved is not None and resolved.name != expected_name:
            errors.append(f"temporary {label} filename must be {expected_name}")

    if not folder.is_dir():
        errors.append(f"document folder not found: {folder}")
    elif vault_root and not inside(folder, vault_root):
        errors.append("document folder is outside --vault-root")
    if inside(report, folder) or (vault_root and inside(report, vault_root)):
        errors.append("temporary conversion report must be outside the document folder and vault")
    if recall_model is not None and (inside(recall_model, folder) or (vault_root and inside(recall_model, vault_root))):
        errors.append("temporary recall model must be outside the document folder and vault")
    if aesthetic_check is not None and (inside(aesthetic_check, folder) or (vault_root and inside(aesthetic_check, vault_root))):
        errors.append("temporary aesthetic check must be outside the document folder and vault")
    for resolved, label in ((render_metrics, "render metrics"), (render_check, "render check")):
        if resolved is not None and (inside(resolved, folder) or (vault_root and inside(resolved, vault_root))):
            errors.append(f"temporary {label} must be outside the document folder and vault")
    if recall_model is not None:
        if not recall_model.is_file():
            errors.append("temporary recall model is missing")
        else:
            try:
                recall_data = json.loads(recall_model.read_text(encoding="utf-8"))
                if not isinstance(recall_data, dict) or recall_data.get("schema_version") != 1:
                    errors.append("temporary recall model must use schema_version 1")
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                errors.append(f"invalid temporary recall model JSON: {exc}")
    if aesthetic_check is not None:
        if not aesthetic_check.is_file():
            errors.append("temporary aesthetic check is missing")
        else:
            try:
                data = json.loads(aesthetic_check.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or data.get("schema_version") != 1:
                    errors.append("temporary aesthetic check must use schema_version 1")
                elif not data.get("valid") or data.get("score", 0) < data.get("minimum_score", 85):
                    errors.append("Canvas aesthetic check did not pass")
                aesthetic_check_data = data
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                errors.append(f"invalid temporary aesthetic check JSON: {exc}")
    for resolved, label, expected_mode in (
        (render_metrics, "render metrics", "measure"),
        (render_check, "render check", "check"),
    ):
        if resolved is None:
            continue
        if not resolved.is_file():
            errors.append(f"temporary {label} is missing")
            continue
        try:
            data = json.loads(resolved.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema_version") != 1:
                errors.append(f"temporary {label} must use schema_version 1")
            elif data.get("mode") != expected_mode or not data.get("measurement_complete"):
                errors.append(f"temporary {label} is incomplete or has the wrong mode")
            elif expected_mode == "check" and not data.get("valid"):
                errors.append("final Obsidian DOM render check did not pass")
            if expected_mode == "measure":
                render_metrics_data = data
            else:
                render_check_data = data
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"invalid temporary {label} JSON: {exc}")

    if not errors:
        forbidden = [path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS]
        if forbidden:
            errors.append("source originals found in document folder: " + ", ".join(path.name for path in forbidden))

        markdown_files = [path for path in folder.glob("*.md") if path.name != "conversion-report.md"]
        canvas_files = list(folder.glob("*.canvas"))
        assets = folder / "assets"
        if len(markdown_files) != 1:
            errors.append(f"expected one primary Markdown file, found {len(markdown_files)}")
        if len(canvas_files) != 1:
            errors.append(f"expected one Canvas file, found {len(canvas_files)}")
        if (folder / "conversion-report.md").exists():
            errors.append("conversion-report.md is temporary QA state and must not be in the document folder")
        if not report.is_file():
            errors.append("temporary conversion report is missing")
        if not assets.is_dir():
            errors.append("assets directory is missing")

        if len(markdown_files) == 1:
            errors += validate_markdown(markdown_files[0], folder, vault_root)
        if len(canvas_files) == 1:
            errors += validate_canvas(canvas_files[0], folder, vault_root)
            canvas_hash = sha256_file(canvas_files[0])
            if aesthetic_check_data is not None and aesthetic_check_data.get("canvas_sha256") != canvas_hash:
                errors.append("aesthetic check does not match the delivered Canvas")
            if render_check_data is not None and render_check_data.get("canvas_sha256") != canvas_hash:
                errors.append("final render check does not match the delivered Canvas")
            if render_metrics_data is not None and not render_metrics_data.get("nodes"):
                errors.append("first-pass render metrics contain no text-node measurements")
        if report.is_file():
            errors += validate_report(report)
        if assets.is_dir() and len(markdown_files) == 1:
            errors += validate_assets(assets, markdown_files[0])

    report_deleted = False
    recall_model_deleted = False
    aesthetic_check_deleted = False
    render_metrics_deleted = False
    render_check_deleted = False
    if not errors and args.delete_qa_on_success:
        report.unlink()
        report_deleted = True
        if recall_model is not None:
            recall_model.unlink()
            recall_model_deleted = True
        if aesthetic_check is not None:
            aesthetic_check.unlink()
            aesthetic_check_deleted = True
        if render_metrics is not None:
            render_metrics.unlink()
            render_metrics_deleted = True
        if render_check is not None:
            render_check.unlink()
            render_check_deleted = True
    result = {
        "valid": not errors,
        "document_folder": str(folder),
        "temporary_report": str(report),
        "report_deleted": report_deleted,
        "temporary_recall_model": str(recall_model) if recall_model else None,
        "recall_model_deleted": recall_model_deleted,
        "aesthetic_check_deleted": aesthetic_check_deleted,
        "render_metrics_deleted": render_metrics_deleted,
        "render_check_deleted": render_check_deleted,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
