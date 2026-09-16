#!/usr/bin/env python3
"""Validate one derived Obsidian course-document folder using only stdlib.

Two contracts live here:

* ``policy-document`` and ``paper`` keep the faithful-transcription contract: one
  note, page markers, ``page-PPP-kind-NN.ext`` assets.
* ``lecture-notes`` uses the content-driven synthesis contract: one or more notes
  planned from the source document's own section outline, no page markers,
  semantic asset names, and a page ledger that accounts for every source page.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path


SOURCE_EXTENSIONS = {
    ".pdf", ".ppt", ".pptx", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".7z", ".rar", ".tar", ".gz",
}
VISUAL_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}
PAGE_ASSET_NAME = re.compile(
    r"^page-(\d{3})-(figure|table|equation|chart|fallback)-(\d{2})\.[a-z0-9]+$"
)
SEMANTIC_ASSET_NAME = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*\.(?:png|jpg|jpeg|webp|gif|bmp|svg)$"
)
REQUIRED_PROPERTIES = {
    "type", "course", "title", "source_filename", "source_format",
    "source_sha256", "conversion_profile", "mineru_model", "status",
}
SYNTHESIS_PROFILE = "lecture-notes"
LEGACY_PROFILES = {"policy-document", "paper"}
PROFILES = {SYNTHESIS_PROFILE} | LEGACY_PROFILES
ALLOWED_EXTRA_SECTIONS = {"In-class notes"}
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
SOURCE_LINK = re.compile(r"\[\[[^\]]+#([^\]|]+)\|Source(?:\s+p\.(\d+))?\]\]")
H2 = re.compile(r"(?m)^##\s+(.+?)\s*$")
BANNED_CANVAS_EDGE_LABELS = {
    "related to", "contains", "contains section", "followed by", "includes asset",
    "connects to", "next", "section",
}
STOPWORDS = {
    "with", "from", "that", "this", "these", "those", "than", "then", "they",
    "their", "there", "them", "when", "where", "which", "while", "will",
    "would", "could", "should", "have", "has", "had", "been", "were", "was",
    "are", "and", "the", "for", "not", "but", "you", "your", "can", "into",
    "more", "most", "some", "such", "also", "each", "other", "only", "over",
    "used", "using", "use", "one", "two", "how", "why", "what", "who", "its",
    "about", "does", "may", "any", "all", "our", "out", "see", "per", "via",
}


class ValidationError(RuntimeError):
    pass


def load_planner():
    path = Path(__file__).resolve().parent / "plan-note-structure.py"
    spec = importlib.util.spec_from_file_location("lecture_skill_note_plan", path)
    if spec is None or spec.loader is None:
        raise ValidationError("cannot load plan-note-structure.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def distinctive_tokens(text: str) -> set[str]:
    lowered = text.lower()
    latin = {token for token in re.findall(r"[a-z][a-z0-9-]{3,}", lowered) if token not in STOPWORDS}
    sequences = re.findall(r"[\u3400-\u9fff]+", text)
    bigrams = {sequence[index : index + 2] for sequence in sequences for index in range(len(sequence) - 1)}
    return latin | bigrams


def flatten_block(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "".join(flatten_block(item) for item in value)
    if isinstance(value, dict):
        if isinstance(value.get("content"), str):
            return value["content"]
        preferred = [
            "title_content", "paragraph_content", "math_content", "code_content",
            "algorithm_content", "list_items", "image_caption", "table_caption",
            "chart_caption", "page_header_content", "page_footer_content",
            "page_footnote_content",
        ]
        for key in preferred:
            if key in value:
                return flatten_block(value[key])
        return "".join(flatten_block(item) for item in value.values())
    return ""


def page_bodies(pages: list) -> list[str]:
    bodies: list[str] = []
    for page in pages:
        blocks: list[dict] = []
        if isinstance(page, list):
            blocks = [item for item in page if isinstance(item, dict)]
        elif isinstance(page, dict):
            for key in ("blocks", "content", "items"):
                if isinstance(page.get(key), list):
                    blocks = [item for item in page[key] if isinstance(item, dict)]
                    break
        bodies.append("\n".join(flatten_block(block.get("content")).strip() for block in blocks))
    return bodies


def validate_markdown(
    path: Path, folder: Path, vault_root: Path | None, mode: str
) -> tuple[list[str], dict[str, str], str, list[int]]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    props, body = parse_frontmatter(text)
    missing = sorted(REQUIRED_PROPERTIES - props.keys())
    if missing:
        errors.append(f"{path.name} missing properties: {', '.join(missing)}")
    if props.get("type") != "course-material":
        errors.append(f"{path.name}: frontmatter type must be course-material")
    source_filename = props.get("source_filename", "")
    if not source_filename or Path(source_filename).name != source_filename:
        errors.append(f"{path.name}: source_filename must be a basename, not a path")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", props.get("source_sha256", "")):
        errors.append(f"{path.name}: source_sha256 must contain 64 hexadecimal characters")
    profile = props.get("conversion_profile")
    if profile not in PROFILES:
        errors.append(f"{path.name}: invalid conversion_profile: {profile!r}")

    h1_count = len(re.findall(r"(?m)^#\s+\S", body))
    if h1_count != 1:
        errors.append(f"{path.name}: expected exactly one H1, found {h1_count}")

    markers = [to_int(value) for value in MARKER.findall(body)]
    if mode == "legacy":
        if not markers:
            errors.append(f"{path.name}: no source-page markers found")
        if markers != sorted(markers):
            errors.append(f"{path.name}: source-page markers are not monotonic")
    elif markers:
        errors.append(
            f"{path.name}: page markers are not part of the content-driven lecture-note contract; "
            "the page ledger carries page coverage instead"
        )

    targets: list[str] = []
    targets += re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body)
    targets += re.findall(r"!\[\[([^\]|#]+)", body)
    for raw in targets:
        target = local_target(raw)
        if target is None:
            continue
        candidate = (folder / target).resolve()
        if not inside(candidate, folder) or not candidate.is_file():
            errors.append(f"{path.name}: unresolved or escaping asset/embed: {target}")

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
                    errors.append(f"{path.name}: unresolved or ambiguous wikilink: {target}")

    return errors, props, body, markers


def validate_note_sections(note_name: str, body: str, sections: list[str]) -> list[str]:
    errors: list[str] = []
    headings = [match.group(1).strip() for match in H2.finditer(body)]
    expected = set(sections)
    extra = sorted({
        heading for heading in headings
        if heading not in expected and heading not in ALLOWED_EXTRA_SECTIONS
    })
    if extra:
        errors.append(f"{note_name}: H2 headings outside the finalized note plan: {', '.join(extra)}")
    missing = [section for section in sections if section not in headings]
    if missing:
        errors.append(f"{note_name}: planned sections are missing as H2 headings: {', '.join(missing)}")
    duplicated = sorted({heading for heading in headings if headings.count(heading) > 1})
    if duplicated:
        errors.append(f"{note_name}: duplicate H2 headings cannot be addressed uniquely: {', '.join(duplicated)}")
    return errors


def normalize_for_match(value: str) -> str:
    """Fold Markdown emphasis, link syntax, and whitespace so quoted phrases can match."""
    text = re.sub(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", lambda match: match.group(2) or match.group(1), value)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`~]+", "", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def validate_page_evidence(ledger: dict, note_texts: dict[str, str]) -> list[str]:
    """Every kept page must quote a phrase that actually appears in its target note."""
    errors: list[str] = []
    for item in ledger.get("pages", []) if isinstance(ledger, dict) else []:
        if not isinstance(item, dict) or item.get("disposition") == "dropped":
            continue
        slug = item.get("note")
        evidence = item.get("evidence")
        if slug not in note_texts or not isinstance(evidence, str) or not evidence.strip():
            continue
        needle = normalize_for_match(evidence)
        haystack = normalize_for_match(note_texts[slug])
        if needle not in haystack:
            errors.append(
                f"page {item.get('page')} evidence does not appear in {slug}: {evidence!r}; "
                "quote text that the delivered note actually contains"
            )
    return errors


def validate_conservation(
    ledger: dict, page_groups: list, note_texts: dict[str, str], threshold: float,
) -> tuple[list[str], list[dict]]:
    errors: list[str] = []
    rows: list[dict] = []
    bodies = page_bodies(page_groups)
    note_tokens = {slug: distinctive_tokens(text) for slug, text in note_texts.items()}
    for item in ledger.get("pages", []):
        if not isinstance(item, dict) or item.get("disposition") == "dropped":
            continue
        page = item.get("page")
        if not isinstance(page, int) or page < 1 or page > len(bodies):
            continue
        slug = item.get("note")
        if slug not in note_tokens:
            continue
        page_tokens = distinctive_tokens(bodies[page - 1])
        recall = 1.0 if not page_tokens else len(page_tokens & note_tokens[slug]) / len(page_tokens)
        rows.append({"page": page, "note": slug, "recall": round(recall, 3)})
        exempt = (
            isinstance(item.get("recall_exempt"), bool)
            and item["recall_exempt"]
            and isinstance(item.get("recall_exempt_reason"), str)
            and bool(item["recall_exempt_reason"].strip())
        )
        if recall + 1e-9 < threshold and not exempt:
            errors.append(
                f"page {page} content is not represented in {slug}: recall {recall:.2f} < {threshold:.2f}; "
                "either fold the missing content into the note or declare recall_exempt with a reason"
            )
    return errors, rows


def rectangles_overlap(a: dict, b: dict) -> bool:
    if a.get("type") == "group" or b.get("type") == "group":
        return False
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


def validate_canvas(path: Path, folder: Path, vault_root: Path | None, note: Path | None) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"invalid canvas JSON: {exc}"]

    nodes = data.get("nodes")
    edges = data.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return ["canvas must contain nodes and edges arrays"]

    note_h2: set[str] = set()
    note_h2_pages: dict[str, set[int]] = {}
    note_page_count = 0
    if note is not None and note.is_file():
        note_text = note.read_text(encoding="utf-8")
        note_h2 = set(re.findall(r"(?m)^##\s+(.+?)\s*$", note_text))
        current_page: int | None = None
        for line in note_text.splitlines():
            marker = re.fullmatch(r"<!--\s*source-page:\s*(\d+)\s*-->", line.strip())
            if marker:
                current_page = to_int(marker.group(1))
                continue
            heading = re.fullmatch(r"##\s+(.+?)\s*", line)
            if heading and current_page is not None:
                note_h2_pages.setdefault(heading.group(1).strip(), set()).add(current_page)
        note_props, _ = parse_frontmatter(note_text)
        note_page_count = to_int(note_props.get("source_pages", "0"))

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
                    source_link = SOURCE_LINK.search(text)
                    if not source_link:
                        errors.append(f"concept node {node_id} is missing a compact source-heading link")
                    elif source_link.group(1) not in note_h2:
                        errors.append(f"concept node {node_id} links an unknown source heading: {source_link.group(1)}")
                    elif source_link.group(2):
                        source_page = to_int(source_link.group(2))
                        if note_page_count and not 1 <= source_page <= note_page_count:
                            errors.append(f"concept node {node_id} source page is outside 1..{note_page_count}")
                        elif (
                            source_link.group(1) in note_h2_pages
                            and source_page not in note_h2_pages[source_link.group(1)]
                        ):
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


def validate_assets(assets: Path, mode: str, page_count: int, referenced: set[str]) -> list[str]:
    errors: list[str] = []
    sequences: dict[tuple[int, str], list[int]] = {}
    seen: set[str] = set()
    for path in assets.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in VISUAL_EXTENSIONS:
            continue
        if path.parent != assets:
            errors.append(f"visual asset must be a flat file directly under assets/: {path.relative_to(assets)}")
            continue
        seen.add(path.name)
        if mode == "synthesis":
            if path.name.startswith("page-"):
                errors.append(f"lecture-notes assets must not use page-number prefixes: {path.name}")
            elif not SEMANTIC_ASSET_NAME.fullmatch(path.name):
                errors.append(f"visual asset filename must be a lowercase semantic kebab-case slug: {path.name}")
            continue
        match = PAGE_ASSET_NAME.fullmatch(path.name)
        if not match:
            errors.append(f"visual asset filename violates page-PPP-kind-NN.ext: {path.name}")
            continue
        page = to_int(match.group(1))
        kind = match.group(2)
        index = to_int(match.group(3))
        if page < 1 or page > page_count:
            errors.append(f"asset page outside 1..{page_count}: {path.name}")
        sequences.setdefault((page, kind), []).append(index)
    for (page, kind), values in sequences.items():
        ordered = sorted(values)
        expected = list(range(1, len(ordered) + 1))
        if ordered != expected:
            errors.append(f"asset sequence for page {page:03d} {kind} must be contiguous from 01: {ordered}")
    if mode == "synthesis":
        orphans = sorted(seen - referenced)
        if orphans:
            errors.append(
                "lecture-notes assets are not referenced by any note or Canvas file node: "
                + ", ".join(orphans)
            )
    return errors


def validate_refinement_chain(reports: list[dict], delivered_sha256: str) -> list[str]:
    errors: list[str] = []
    if not reports:
        return errors
    terminals = [report for report in reports if report.get("refined_sha256") == delivered_sha256]
    if len(terminals) != 1:
        errors.append("refinement report does not match the delivered Markdown")
        return errors
    terminal = terminals[0]
    for report in reports:
        if report is terminal:
            continue
        if report.get("refined_sha256") != terminal.get("snapshot_sha256"):
            errors.append("refinement reports do not form a single snapshot-to-refined chain")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_folder", type=Path)
    parser.add_argument("--vault-root", type=Path)
    parser.add_argument("--fixture-mode", action="store_true", help="Allow document-relative Canvas paths in tests only")
    parser.add_argument("--report", required=True, type=Path, help="Temporary QA report outside the vault")
    parser.add_argument("--plan", type=Path, help="Finalized note plan from plan-note-structure.py")
    parser.add_argument("--ledger", type=Path, help="Finalized page ledger from plan-note-structure.py")
    parser.add_argument("--page-groups", type=Path, help="Normalized MinerU page groups for content conservation")
    parser.add_argument("--conservation-threshold", type=float, default=0.35)
    parser.add_argument("--allow-heavy-drop", action="store_true")
    parser.add_argument("--recall-model", type=Path, help="Temporary Agent-authored recall model outside the vault")
    parser.add_argument("--layout-refinement-report", type=Path, help="Optional validated multimodal layout report")
    parser.add_argument("--latex-refinement-report", type=Path, help="Optional validated LaTeX normalization report")
    parser.add_argument("--aesthetic-check", type=Path, help="Static Canvas aesthetic check outside the vault")
    parser.add_argument("--render-metrics", type=Path, help="First-pass Obsidian DOM measurements outside the vault")
    parser.add_argument("--render-check", type=Path, help="Final Obsidian DOM readability check outside the vault")
    parser.add_argument(
        "--delete-qa-on-success", "--delete-report-on-success",
        dest="delete_qa_on_success", action="store_true",
        help="Delete the report and supplied staging QA files after every check passes",
    )
    args = parser.parse_args()

    folder = args.document_folder.resolve()
    vault_root = args.vault_root.resolve() if args.vault_root else None
    report_input = args.report
    report = report_input.resolve()
    recall_model_input = args.recall_model
    recall_model = recall_model_input.resolve() if recall_model_input else None
    layout_report_input = args.layout_refinement_report
    layout_report = layout_report_input.resolve() if layout_report_input else None
    latex_report_input = args.latex_refinement_report
    latex_report = latex_report_input.resolve() if latex_report_input else None
    aesthetic_check_input = args.aesthetic_check
    aesthetic_check = aesthetic_check_input.resolve() if aesthetic_check_input else None
    render_metrics_input = args.render_metrics
    render_metrics = render_metrics_input.resolve() if render_metrics_input else None
    render_check_input = args.render_check
    render_check = render_check_input.resolve() if render_check_input else None
    plan_path = args.plan.resolve() if args.plan else None
    ledger_path = args.ledger.resolve() if args.ledger else None
    page_groups_path = args.page_groups.resolve() if args.page_groups else None
    render_metrics_data: dict | None = None
    render_check_data: dict | None = None
    aesthetic_check_data: dict | None = None
    layout_report_data: dict | None = None
    latex_report_data: dict | None = None
    conservation_rows: list[dict] = []
    conservation_mode = "not-checked"
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
    if layout_report_input is not None and layout_report_input.is_symlink():
        errors.append("temporary layout refinement report must not be a symlink")
    if layout_report is not None and layout_report.name != "layout-refinement-report.json":
        errors.append("temporary layout refinement report filename must be layout-refinement-report.json")
    if latex_report_input is not None and latex_report_input.is_symlink():
        errors.append("temporary LaTeX refinement report must not be a symlink")
    if latex_report is not None and latex_report.name != "latex-refinement-report.json":
        errors.append("temporary LaTeX refinement report filename must be latex-refinement-report.json")
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
    for resolved, label in (
        (recall_model, "temporary recall model"),
        (layout_report, "temporary layout refinement report"),
        (latex_report, "temporary LaTeX refinement report"),
        (aesthetic_check, "temporary aesthetic check"),
        (render_metrics, "temporary render metrics"),
        (render_check, "temporary render check"),
        (plan_path, "temporary note plan"),
        (ledger_path, "temporary page ledger"),
        (page_groups_path, "temporary page groups"),
    ):
        if resolved is None:
            continue
        if inside(resolved, folder) or (vault_root and inside(resolved, vault_root)):
            errors.append(f"{label} must be outside the document folder and vault")
    for resolved, label in (
        (plan_path, "temporary note plan"),
        (ledger_path, "temporary page ledger"),
    ):
        if resolved is not None and not resolved.is_file():
            errors.append(f"{label} is missing")
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
    for report_path, label, expected_mode in (
        (layout_report, "temporary layout refinement report", None),
        (latex_report, "temporary LaTeX refinement report", None),
        (aesthetic_check, "temporary aesthetic check", None),
        (render_metrics, "temporary render metrics", "measure"),
        (render_check, "temporary render check", "check"),
    ):
        if report_path is None:
            continue
        if not report_path.is_file():
            errors.append(f"{label} is missing")
            continue
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"invalid {label} JSON: {exc}")
            continue
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            errors.append(f"{label} must use schema_version 1")
            continue
        if report_path is layout_report:
            if not data.get("valid"):
                errors.append("optional multimodal layout refinement did not pass")
            layout_report_data = data
        elif report_path is latex_report:
            if not data.get("valid"):
                errors.append("optional LaTeX refinement did not pass")
            latex_report_data = data
        elif report_path is aesthetic_check:
            if not data.get("valid") or data.get("score", 0) < data.get("minimum_score", 85):
                errors.append("Canvas aesthetic check did not pass")
            aesthetic_check_data = data
        else:
            if data.get("mode") != expected_mode or not data.get("measurement_complete"):
                errors.append(f"{label} is incomplete or has the wrong mode")
            elif expected_mode == "check" and not data.get("valid"):
                errors.append("final Obsidian DOM render check did not pass")
            if expected_mode == "measure":
                render_metrics_data = data
            else:
                render_check_data = data

    if not errors:
        hidden_entries = [
            path for path in folder.rglob("*")
            if any(part.startswith(".") for part in path.relative_to(folder).parts)
        ]
        if hidden_entries:
            errors.append(
                "dot-prefixed files/directories are forbidden in the document folder: "
                + ", ".join(str(path.relative_to(folder)) for path in hidden_entries)
            )
        forbidden = [path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS]
        if forbidden:
            errors.append("source originals found in document folder: " + ", ".join(path.name for path in forbidden))

        markdown_files = [path for path in folder.glob("*.md") if path.name != "conversion-report.md"]
        canvas_files = list(folder.glob("*.canvas"))
        assets = folder / "assets"
        if (folder / "conversion-report.md").exists():
            errors.append("conversion-report.md is temporary QA state and must not be in the document folder")
        if not report.is_file():
            errors.append("temporary conversion report is missing")
        if not assets.is_dir():
            errors.append("assets directory is missing")
        if not markdown_files:
            errors.append("expected at least one primary Markdown file, found 0")
        if len(canvas_files) != len(markdown_files):
            errors.append(
                f"expected one Canvas per note, found {len(canvas_files)} Canvas files for {len(markdown_files)} notes"
            )

        bodies: dict[str, str] = {}
        note_texts: dict[str, str] = {}
        # Content-driven notes carry a plan and a ledger; page markers exist only in the
        # MinerU faithful-transcription path.
        marker_free = not any(MARKER.search(note.read_text(encoding="utf-8")) for note in markdown_files)
        mode = "synthesis" if (plan_path is not None and ledger_path is not None) or marker_free else "legacy"
        for note in markdown_files:
            note_errors, _props, body, _markers = validate_markdown(note, folder, vault_root, mode)
            bodies[note.stem] = body
            note_texts[note.stem] = note.read_text(encoding="utf-8")
            errors += note_errors

        if mode == "legacy":
            if len(markdown_files) != 1:
                errors.append(f"expected one primary Markdown file, found {len(markdown_files)}")
            for note in markdown_files:
                note_props, _ = parse_frontmatter(note.read_text(encoding="utf-8"))
                page_count = to_int(note_props.get("source_pages", "0"))
                if page_count <= 0:
                    errors.append(f"{note.name}: source_pages must be a positive integer")
                markers = [to_int(value) for value in MARKER.findall(bodies.get(note.stem, ""))]
                invalid = [value for value in markers if value < 1 or value > page_count]
                if invalid:
                    errors.append(f"{note.name}: source-page markers outside 1..{page_count}: {invalid}")
                errors += validate_refinement_chain(
                    [entry for entry in (layout_report_data, latex_report_data) if entry is not None],
                    sha256_file(note),
                )
        else:
            planner = None
            try:
                planner = load_planner()
            except ValidationError as exc:
                errors.append(str(exc))
            if planner is not None:
                if plan_path is None or ledger_path is None:
                    errors.append(
                        "a note without page markers requires --plan and --ledger from plan-note-structure.py"
                    )
                elif plan_path.is_file() and ledger_path.is_file():
                    try:
                        plan = json.loads(plan_path.read_text(encoding="utf-8"))
                        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                        errors.append(f"invalid note plan or page ledger JSON: {exc}")
                        plan = None
                        ledger = {}
                    if plan is not None:
                        errors += planner.validate_plan(plan)
                        errors += planner.validate_ledger(ledger, plan, args.allow_heavy_drop)
                        slugs = [
                            note["slug"] for note in plan.get("notes", [])
                            if isinstance(note, dict) and isinstance(note.get("slug"), str)
                        ]
                        note_stems = set(bodies)
                        unexpected = sorted(note_stems - set(slugs))
                        if unexpected:
                            errors.append(
                                "document folder contains notes outside the note plan: " + ", ".join(unexpected)
                            )
                        missing = [slug for slug in slugs if slug not in note_stems]
                        if missing:
                            errors.append("planned notes are missing from the document folder: " + ", ".join(missing))
                        for note in plan.get("notes", []):
                            if not isinstance(note, dict) or note.get("slug") not in bodies:
                                continue
                            sections = [
                                section["heading"]
                                for section in note.get("sections", [])
                                if isinstance(section, dict) and isinstance(section.get("heading"), str)
                            ]
                            errors += validate_note_sections(note["slug"], bodies[note["slug"]], sections)
                        errors += validate_page_evidence(ledger, note_texts)
                        if page_groups_path is None:
                            conservation_mode = "evidence"
                        elif not page_groups_path.is_file():
                            errors.append("temporary page groups file is missing")
                        else:
                            try:
                                page_groups = json.loads(page_groups_path.read_text(encoding="utf-8"))
                            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                                errors.append(f"invalid page groups JSON: {exc}")
                            else:
                                conservation_mode = "evidence+mineru-text"
                                conservation_errors, conservation_rows = validate_conservation(
                                    ledger, page_groups, note_texts, args.conservation_threshold
                                )
                                errors += conservation_errors

        for canvas_path in canvas_files:
            note = folder / f"{canvas_path.stem}.md"
            errors += validate_canvas(canvas_path, folder, vault_root, note if note.is_file() else None)
            canvas_hash = sha256_file(canvas_path)
            if aesthetic_check_data is not None and aesthetic_check_data.get("canvas_sha256") != canvas_hash:
                errors.append("aesthetic check does not match the delivered Canvas")
            if render_check_data is not None and render_check_data.get("canvas_sha256") != canvas_hash:
                errors.append("final render check does not match the delivered Canvas")
            if render_metrics_data is not None and not render_metrics_data.get("nodes"):
                errors.append("first-pass render metrics contain no text-node measurements")

        if report.is_file():
            errors += validate_report(report)
        if assets.is_dir():
            referenced: set[str] = set()
            for text in note_texts.values():
                referenced.update(Path(raw).name for raw in re.findall(r"!\[\[([^\]|#]+)", text))
                referenced.update(Path(raw).name for raw in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text))
            for canvas_path in canvas_files:
                try:
                    canvas_data = json.loads(canvas_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                for node in canvas_data.get("nodes", []):
                    if isinstance(node, dict) and node.get("type") == "file":
                        referenced.add(Path(str(node.get("file", ""))).name)
            page_count = 0
            for note in markdown_files:
                note_props, _ = parse_frontmatter(note.read_text(encoding="utf-8"))
                page_count = max(page_count, to_int(note_props.get("source_pages", "0")))
            if ledger_path is not None and ledger_path.is_file():
                try:
                    page_count = max(
                        page_count,
                        to_int(json.loads(ledger_path.read_text(encoding="utf-8")).get("source_pages", "0")),
                    )
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            errors += validate_assets(assets, mode, page_count, referenced)

    deleted: dict[str, bool] = {}
    if not errors and args.delete_qa_on_success:
        for label, resolved in (
            ("report", report),
            ("recall_model", recall_model),
            ("layout_report", layout_report),
            ("latex_report", latex_report),
            ("aesthetic_check", aesthetic_check),
            ("render_metrics", render_metrics),
            ("render_check", render_check),
            ("plan", plan_path),
            ("ledger", ledger_path),
            ("page_groups", page_groups_path),
        ):
            if resolved is not None:
                resolved.unlink()
                deleted[label] = True
    result = {
        "valid": not errors,
        "document_folder": str(folder),
        "temporary_report": str(report),
        "report_deleted": deleted.get("report", False),
        "temporary_recall_model": str(recall_model) if recall_model else None,
        "recall_model_deleted": deleted.get("recall_model", False),
        "layout_refinement_report_deleted": deleted.get("layout_report", False),
        "latex_refinement_report_deleted": deleted.get("latex_report", False),
        "aesthetic_check_deleted": deleted.get("aesthetic_check", False),
        "render_metrics_deleted": deleted.get("render_metrics", False),
        "render_check_deleted": deleted.get("render_check", False),
        "note_plan_deleted": deleted.get("plan", False),
        "page_ledger_deleted": deleted.get("ledger", False),
        "conservation_mode": conservation_mode,
        "content_conservation": conservation_rows,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
