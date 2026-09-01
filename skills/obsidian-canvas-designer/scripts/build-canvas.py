#!/usr/bin/env python3
"""Render a deterministic knowledge-recall Canvas from an Agent-authored semantic model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path


PROFILES = ("lecture-notes", "policy-document", "paper")
MODES = ("pre-class", "post-class")
CONCEPT_KINDS = {
    "foundation", "concept", "mechanism", "process", "evidence", "example",
    "application", "comparison", "boundary", "misconception", "decision",
    "claim", "method", "finding", "limitation", "rule", "exception",
}
RELATION_TYPES = {
    "requires", "causes", "enables", "explains", "supports", "contrasts",
    "limits", "example-of", "part-of", "leads-to", "qualifies", "applies-to",
}
BANNED_RELATION_LABELS = {
    "related to", "contains", "contains section", "followed by", "includes asset",
    "connects to", "next", "section",
}
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,47}$")
HEADING_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")


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


def clean_heading(value: str) -> str:
    return re.sub(r"^#{1,6}\s+", "", value.strip())


def validate_visual_title(value: str, label: str) -> None:
    has_cjk = bool(re.search(r"[\u3400-\u9fff]", value))
    maximum = 30 if has_cjk else 60
    if len(value) > maximum:
        raise CanvasBuildError(f"{label} is too long for a readable concept card; maximum {maximum} characters")


def require_text(value, label: str, minimum: int = 1, maximum: int = 500) -> str:
    if not isinstance(value, str):
        raise CanvasBuildError(f"{label} must be text")
    result = value.strip()
    if len(result) < minimum or len(result) > maximum:
        raise CanvasBuildError(f"{label} must contain {minimum}..{maximum} characters")
    if "[Populate" in result or "[Replace" in result or "TODO" in result:
        raise CanvasBuildError(f"{label} contains a placeholder")
    return result


def require_text_list(value, label: str, minimum: int, maximum: int, item_maximum: int = 220) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise CanvasBuildError(f"{label} must contain {minimum}..{maximum} items")
    return [require_text(item, f"{label}[{index}]", maximum=item_maximum) for index, item in enumerate(value)]


def note_headings(markdown: str) -> list[str]:
    return [match.group(1).strip() for match in HEADING_RE.finditer(markdown)]


def note_heading_pages(markdown: str) -> dict[str, set[int]]:
    result: dict[str, set[int]] = {}
    current_page: int | None = None
    for line in markdown.splitlines():
        marker = re.fullmatch(r"<!--\s*source-page:\s*(\d+)\s*-->", line.strip())
        if marker:
            current_page = int(marker.group(1))
            continue
        heading = re.fullmatch(r"##\s+(.+?)\s*", line)
        if heading and current_page is not None:
            result.setdefault(heading.group(1).strip(), set()).add(current_page)
    return result


def note_page_count(markdown: str) -> int | None:
    frontmatter = re.search(r"(?m)^source_pages:\s*[\"']?(\d+)", markdown)
    if frontmatter:
        return int(frontmatter.group(1))
    markers = [int(value) for value in re.findall(r"<!--\s*source-page:\s*(\d+)\s*-->", markdown)]
    return max(markers) if markers else None


def validate_model(model: dict, markdown: str, profile: str) -> dict:
    if not isinstance(model, dict) or model.get("schema_version") != 1:
        raise CanvasBuildError("recall model must be an object with schema_version 1")
    if model.get("profile") != profile:
        raise CanvasBuildError("recall model profile does not match --profile")
    if model.get("mode") not in MODES:
        raise CanvasBuildError("recall model mode must be pre-class or post-class")
    require_text(model.get("title"), "title", maximum=160)

    orientation = model.get("orientation")
    if not isinstance(orientation, dict):
        raise CanvasBuildError("orientation must be an object")
    require_text(orientation.get("central_question"), "orientation.central_question", 8, 240)
    require_text(orientation.get("one_sentence_answer"), "orientation.one_sentence_answer", 12, 240)
    require_text_list(orientation.get("takeaways"), "orientation.takeaways", 3, 5, 160)

    groups = model.get("groups")
    if not isinstance(groups, list) or not 2 <= len(groups) <= 7:
        raise CanvasBuildError("groups must contain 2..7 learning modules")
    group_ids: set[str] = set()
    group_orders: set[int] = set()
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            raise CanvasBuildError(f"groups[{index}] must be an object")
        group_id = group.get("id")
        if not isinstance(group_id, str) or not KEY_RE.fullmatch(group_id) or group_id in group_ids:
            raise CanvasBuildError(f"groups[{index}].id must be a unique lowercase slug")
        group_ids.add(group_id)
        require_text(group.get("title"), f"groups[{index}].title", maximum=80)
        require_text(group.get("summary"), f"groups[{index}].summary", 12, 120)
        order = group.get("order")
        if not isinstance(order, int) or order < 1 or order in group_orders:
            raise CanvasBuildError(f"groups[{index}].order must be a unique positive integer")
        group_orders.add(order)
    if group_orders != set(range(1, len(groups) + 1)):
        raise CanvasBuildError("group orders must be contiguous from 1")

    concepts = model.get("concepts")
    if not isinstance(concepts, list) or not 4 <= len(concepts) <= 20:
        raise CanvasBuildError("concepts must contain 4..20 atomic recall nodes")
    concept_ids: set[str] = set()
    concept_groups: set[str] = set()
    concept_kinds: set[str] = set()
    source_headings = set(note_headings(markdown))
    heading_pages = note_heading_pages(markdown)
    page_count = note_page_count(markdown)
    for index, concept in enumerate(concepts):
        if not isinstance(concept, dict):
            raise CanvasBuildError(f"concepts[{index}] must be an object")
        concept_id = concept.get("id")
        if not isinstance(concept_id, str) or not KEY_RE.fullmatch(concept_id) or concept_id in concept_ids:
            raise CanvasBuildError(f"concepts[{index}].id must be a unique lowercase slug")
        concept_ids.add(concept_id)
        group_id = concept.get("group")
        if group_id not in group_ids:
            raise CanvasBuildError(f"concepts[{index}].group is unknown: {group_id!r}")
        concept_groups.add(group_id)
        kind = concept.get("kind")
        if kind not in CONCEPT_KINDS:
            raise CanvasBuildError(f"concepts[{index}].kind is unsupported: {kind!r}")
        concept_kinds.add(kind)
        title = require_text(concept.get("title"), f"concepts[{index}].title", maximum=90)
        validate_visual_title(title, f"concepts[{index}].title")
        require_text(concept.get("statement"), f"concepts[{index}].statement", 12, 180)
        require_text_list(concept.get("details", []), f"concepts[{index}].details", 0, 2, 140)
        require_text(concept.get("recall_cue"), f"concepts[{index}].recall_cue", 4, 160)
        heading = require_text(concept.get("source_heading"), f"concepts[{index}].source_heading", maximum=180)
        if clean_heading(heading) not in source_headings:
            raise CanvasBuildError(f"concepts[{index}].source_heading does not exist in the note: {heading!r}")
        source_page = concept.get("source_page")
        if not isinstance(source_page, int) or source_page < 1:
            raise CanvasBuildError(f"concepts[{index}].source_page must be a positive integer")
        if page_count is not None and source_page > page_count:
            raise CanvasBuildError(f"concepts[{index}].source_page is outside 1..{page_count}")
        if clean_heading(heading) in heading_pages and source_page not in heading_pages[clean_heading(heading)]:
            raise CanvasBuildError(
                f"concepts[{index}] source heading/page pair does not occur in the note: "
                f"{clean_heading(heading)!r} on page {source_page}"
            )
    if concept_groups != group_ids:
        missing = ", ".join(sorted(group_ids - concept_groups))
        raise CanvasBuildError(f"every learning module needs at least one concept; empty: {missing}")
    if len(concept_kinds) < 3:
        raise CanvasBuildError("use at least three concept kinds to avoid a flat section outline")

    relations = model.get("relations")
    if not isinstance(relations, list) or not len(concepts) - 1 <= len(relations) <= len(concepts) * 2:
        raise CanvasBuildError("relations must form a selective connected map, between N-1 and 2N edges")
    adjacency = {concept_id: set() for concept_id in concept_ids}
    relation_pairs: set[tuple[str, str, str]] = set()
    for index, relation in enumerate(relations):
        if not isinstance(relation, dict):
            raise CanvasBuildError(f"relations[{index}] must be an object")
        source = relation.get("from")
        target = relation.get("to")
        relation_type = relation.get("type")
        if source not in concept_ids or target not in concept_ids or source == target:
            raise CanvasBuildError(f"relations[{index}] must connect two different known concepts")
        if relation_type not in RELATION_TYPES:
            raise CanvasBuildError(f"relations[{index}].type is unsupported: {relation_type!r}")
        label = require_text(relation.get("label"), f"relations[{index}].label", 2, 42)
        if label.casefold() in BANNED_RELATION_LABELS:
            raise CanvasBuildError(f"relations[{index}].label is structurally generic: {label!r}")
        require_text(relation.get("why"), f"relations[{index}].why", 8, 240)
        key = (source, target, relation_type)
        if key in relation_pairs:
            raise CanvasBuildError(f"duplicate semantic relation: {source} -> {target} ({relation_type})")
        relation_pairs.add(key)
        adjacency[source].add(target)
        adjacency[target].add(source)
    visited: set[str] = set()
    stack = [next(iter(concept_ids))]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        stack.extend(adjacency[current] - visited)
    if visited != concept_ids:
        raise CanvasBuildError("concept relation graph must be connected; isolated islands reduce recall")
    if max(len(neighbours) for neighbours in adjacency.values()) > 6:
        raise CanvasBuildError("a concept has more than six connections; split or prioritize the map")

    coverage = model.get("coverage")
    if not isinstance(coverage, list):
        raise CanvasBuildError("coverage must inventory every H2 section")
    covered_headings: set[str] = set()
    covered_sections: set[tuple[str, int]] = set()
    for index, item in enumerate(coverage):
        if not isinstance(item, dict):
            raise CanvasBuildError(f"coverage[{index}] must be an object")
        heading = require_text(item.get("source_heading"), f"coverage[{index}].source_heading", maximum=180)
        source_page = item.get("source_page")
        if heading not in source_headings:
            raise CanvasBuildError(f"coverage[{index}] heading is missing from the note: {heading!r}")
        if not isinstance(source_page, int) or source_page < 1:
            raise CanvasBuildError(f"coverage[{index}].source_page must be a positive integer")
        if page_count is not None and source_page > page_count:
            raise CanvasBuildError(f"coverage[{index}].source_page is outside 1..{page_count}")
        if heading in heading_pages and source_page not in heading_pages[heading]:
            raise CanvasBuildError(
                f"coverage[{index}] heading/page pair does not occur in the note: {heading!r} on page {source_page}"
            )
        section_key = (heading, source_page)
        if section_key in covered_sections:
            raise CanvasBuildError(f"coverage[{index}] duplicates a heading/page pair: {heading!r} on page {source_page}")
        covered_headings.add(heading)
        covered_sections.add(section_key)
        mapped = item.get("concepts", [])
        omission = item.get("omission_reason")
        if not isinstance(mapped, list) or any(value not in concept_ids for value in mapped):
            raise CanvasBuildError(f"coverage[{index}].concepts contains an unknown concept")
        if not mapped and not (isinstance(omission, str) and omission.strip()):
            raise CanvasBuildError(f"coverage[{index}] needs mapped concepts or an omission_reason")
    if heading_pages:
        expected_sections = {
            (heading, source_page)
            for heading, pages in heading_pages.items()
            for source_page in pages
        }
        if covered_sections != expected_sections:
            missing = ", ".join(
                f"{heading} (page {source_page})"
                for heading, source_page in sorted(expected_sections - covered_sections)
            )
            raise CanvasBuildError(f"coverage is missing note sections: {missing}")
    elif covered_headings != source_headings:
        missing = ", ".join(sorted(source_headings - covered_headings))
        raise CanvasBuildError(f"coverage is missing note sections: {missing}")

    synthesis = model.get("synthesis")
    if not isinstance(synthesis, dict):
        raise CanvasBuildError("synthesis must be an object")
    require_text_list(synthesis.get("logic_chain"), "synthesis.logic_chain", 3, 7, 180)
    distinctions = synthesis.get("distinctions")
    if not isinstance(distinctions, list) or not 1 <= len(distinctions) <= 3:
        raise CanvasBuildError("synthesis.distinctions must contain 1..3 high-value contrasts")
    for index, item in enumerate(distinctions):
        if not isinstance(item, dict):
            raise CanvasBuildError(f"synthesis.distinctions[{index}] must be an object")
        require_text(item.get("terms"), f"synthesis.distinctions[{index}].terms", 3, 100)
        require_text(item.get("rule"), f"synthesis.distinctions[{index}].rule", 8, 220)
    require_text_list(synthesis.get("recall_prompts"), "synthesis.recall_prompts", 3, 5, 180)
    in_class_additions = require_text_list(
        synthesis.get("in_class_additions", []), "synthesis.in_class_additions", 0, 5, 180
    )
    if model["mode"] == "pre-class" and in_class_additions:
        raise CanvasBuildError("pre-class recall models cannot contain invented in-class additions")

    asset_links = model.get("asset_links", [])
    if not isinstance(asset_links, list) or len(asset_links) > 6:
        raise CanvasBuildError("asset_links must contain at most six memory-critical visuals")
    asset_paths: set[str] = set()
    for index, item in enumerate(asset_links):
        if not isinstance(item, dict) or item.get("concept") not in concept_ids:
            raise CanvasBuildError(f"asset_links[{index}] must reference a known concept")
        path = require_text(item.get("path"), f"asset_links[{index}].path", maximum=240)
        if Path(path).is_absolute() or ".." in Path(path).parts or Path(path).parts[:1] != ("assets",):
            raise CanvasBuildError(f"asset_links[{index}].path must be document-relative under assets/")
        if path in asset_paths:
            raise CanvasBuildError(f"asset_links[{index}].path is duplicated: {path}")
        asset_paths.add(path)
        require_text(item.get("caption"), f"asset_links[{index}].caption", 4, 180)

    return model


def text_height(text: str, width: int, minimum: int = 160, maximum: int = 900) -> int:
    approximate_chars_per_line = max(24, width // 9)
    lines = 0
    list_items = 0
    for raw_line in text.splitlines():
        lines += max(1, (len(raw_line) + approximate_chars_per_line - 1) // approximate_chars_per_line)
        if raw_line.lstrip().startswith(("- ", "1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ")):
            list_items += 1
    estimated = 70 + lines * 30 + list_items * 6
    return max(minimum, min(maximum, int(math.ceil(estimated / 10) * 10)))


def render_height(metrics: dict | None, node_id: str, text: str, width: int, estimated: int) -> int:
    if metrics is None:
        return estimated
    records = {item.get("id"): item for item in metrics.get("nodes", []) if isinstance(item, dict)}
    record = records.get(node_id)
    if record is None:
        raise CanvasBuildError(f"render metrics are missing text node {node_id}")
    if record.get("width") != width:
        raise CanvasBuildError(f"render metric width mismatch for text node {node_id}")
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if record.get("text_sha256") != text_hash:
        raise CanvasBuildError(f"render metric text mismatch for text node {node_id}")
    required = record.get("required_height")
    if not isinstance(required, int) or required <= 0:
        raise CanvasBuildError(f"render metrics contain an invalid height for text node {node_id}")
    return required


def concept_color(kind: str) -> str:
    if kind in {"boundary", "misconception", "limitation", "exception"}:
        return "1"
    if kind in {"example", "application", "evidence", "finding"}:
        return "4"
    if kind in {"mechanism", "process", "method"}:
        return "5"
    if kind in {"claim", "decision", "comparison"}:
        return "6"
    if kind == "rule":
        return "2"
    return "3"


def group_color(concepts: list[dict]) -> str:
    counts: dict[str, int] = {}
    for concept in concepts:
        color = concept_color(concept["kind"])
        counts[color] = counts.get(color, 0) + 1
    return sorted(counts, key=lambda color: (-counts[color], color))[0] if counts else "3"


def edge_sides(source: dict, target: dict) -> tuple[str, str]:
    source_x = source["x"] + source["width"] / 2
    source_y = source["y"] + source["height"] / 2
    target_x = target["x"] + target["width"] / 2
    target_y = target["y"] + target["height"] / 2
    dx = target_x - source_x
    dy = target_y - source_y
    if abs(dx) >= abs(dy):
        return ("right", "left") if dx >= 0 else ("left", "right")
    return ("bottom", "top") if dy >= 0 else ("top", "bottom")


def build_canvas(
    note: Path,
    vault_root: Path,
    profile: str,
    model: dict,
    assets_dir: Path | None = None,
    render_metrics: dict | None = None,
) -> dict:
    note = note.resolve()
    vault_root = vault_root.resolve()
    if not note.is_file() or not inside(note, vault_root):
        raise CanvasBuildError("note must be an existing file inside vault_root")
    markdown = note.read_text(encoding="utf-8")
    model = validate_model(model, markdown, profile)
    if render_metrics is not None:
        if render_metrics.get("schema_version") != 1 or not render_metrics.get("measurement_complete"):
            raise CanvasBuildError("render metrics are incomplete or use an unsupported schema")
        if render_metrics.get("mode") != "measure":
            raise CanvasBuildError("build-canvas requires first-pass measure metrics")
    note_relative = note.relative_to(vault_root).as_posix()
    document_folder = note.parent
    assets_dir = assets_dir.resolve() if assets_dir else document_folder / "assets"
    if not assets_dir.is_dir() or not inside(assets_dir, document_folder):
        raise CanvasBuildError("assets directory must exist inside the document folder")

    groups = sorted(model["groups"], key=lambda item: item["order"])
    concepts_by_group = {
        group["id"]: [item for item in model["concepts"] if item["group"] == group["id"]]
        for group in groups
    }
    asset_links: dict[str, list[dict]] = {}
    for item in model.get("asset_links", []):
        asset_links.setdefault(item["concept"], []).append(item)

    group_nodes: list[dict] = []
    content_nodes: list[dict] = []
    edges: list[dict] = []
    node_by_key: dict[str, dict] = {}
    group_bottoms: list[int] = []
    group_width = 520
    group_gap = 160
    group_y = 520

    for group_index, group in enumerate(groups):
        group_x = group_index * (group_width + group_gap)
        child_y = group_y + 90
        child_nodes: list[dict] = []
        for concept in concepts_by_group[group["id"]]:
            details = "\n".join(f"- {value}" for value in concept["details"])
            source_heading = clean_heading(concept["source_heading"])
            parts = [
                "<!-- recall-map: concept -->",
                f"<!-- recall-kind: {concept['kind']} -->",
                f"### {concept['title']}",
                concept["statement"],
            ]
            if details:
                parts += ["", details]
            compact_source = f"[[{note_relative}#{source_heading}|Source p.{concept['source_page']}]]"
            parts += ["", compact_source]
            text = "\n".join(parts)
            node_id = stable_id("concept", f"{note_relative}:{concept['id']}")
            height = render_height(
                render_metrics,
                node_id,
                text,
                440,
                text_height(text, 440, minimum=180, maximum=720),
            )
            node = {
                "id": node_id,
                "type": "text",
                "x": group_x + 40,
                "y": child_y,
                "width": 440,
                "height": height,
                "text": text,
                "color": concept_color(concept["kind"]),
            }
            child_nodes.append(node)
            node_by_key[concept["id"]] = node
            child_y += height + 70

            for asset_index, asset_link in enumerate(asset_links.get(concept["id"], []), start=1):
                asset = (document_folder / asset_link["path"]).resolve()
                if not asset.is_file() or not inside(asset, assets_dir):
                    raise CanvasBuildError(f"memory-critical asset is missing or outside assets/: {asset_link['path']}")
                asset_node_id = stable_id("asset", f"{note_relative}:{asset_link['path']}")
                asset_node = {
                    "id": asset_node_id,
                    "type": "file",
                    "x": group_x + 40,
                    "y": child_y,
                    "width": 440,
                    "height": 260,
                    "file": asset.relative_to(vault_root).as_posix(),
                    "color": "4",
                }
                child_nodes.append(asset_node)
                edges.append(
                    {
                        "id": stable_id("edge", f"{node_id}->{asset_node_id}:visualizes:{asset_index}"),
                        "fromNode": node_id,
                        "fromSide": "bottom",
                        "toNode": asset_node_id,
                        "toSide": "top",
                        "toEnd": "arrow",
                        "label": f"visualized by: {asset_link['caption'][:28]}",
                        "color": "4",
                    }
                )
                child_y += 330
        group_height = child_y - group_y + 20
        group_nodes.append(
            {
                "id": stable_id("group", f"{note_relative}:{group['id']}"),
                "type": "group",
                "x": group_x,
                "y": group_y,
                "width": group_width,
                "height": group_height,
                "label": f"{group['order']:02d} · {group['title']}",
                "color": group_color(concepts_by_group[group["id"]]),
            }
        )
        content_nodes.extend(child_nodes)
        group_bottoms.append(group_y + group_height)

    total_width = max(1600, len(groups) * (group_width + group_gap) - group_gap)
    orientation = model["orientation"]
    overview_width = min(1040, total_width - 500)
    overview_text = "\n".join(
        [
            "<!-- recall-map: overview -->",
            "# One-minute recall",
            f"**Central question:** {orientation['central_question']}",
            f"**Answer:** {orientation['one_sentence_answer']}",
            "",
            "**Takeaways**",
            *[f"- {item}" for item in orientation["takeaways"]],
        ]
    )
    overview_node = {
        "id": stable_id("overview", note_relative),
        "type": "text",
        "x": 0,
        "y": 0,
        "width": overview_width,
        "height": render_height(
            render_metrics,
            stable_id("overview", note_relative),
            overview_text,
            overview_width,
            text_height(overview_text, overview_width, 300, 700),
        ),
        "text": overview_text,
        "color": "6",
    }
    file_node = {
        "id": stable_id("file", note_relative),
        "type": "file",
        "x": overview_node["width"] + 80,
        "y": 0,
        "width": 420,
        "height": overview_node["height"],
        "file": note_relative,
        "color": "1",
    }

    synthesis_y = max(group_bottoms) + 180
    synthesis = model["synthesis"]
    summary_gap = 60
    summary_width = int((total_width - summary_gap * 2) / 3)
    logic_text = "\n".join(
        [
            "<!-- recall-map: synthesis -->",
            "# Logic chain",
            *[f"{index}. {item}" for index, item in enumerate(synthesis["logic_chain"], start=1)],
        ]
    )
    distinction_text = "\n".join(
        [
            "<!-- recall-map: distinctions -->",
            "# Distinctions and boundaries",
            *[f"- **{item['terms']}:** {item['rule']}" for item in synthesis["distinctions"]],
        ]
    )
    recall_lines = [
        "<!-- recall-map: prompts -->",
        "# Active recall",
        *[f"- {item}" for item in synthesis["recall_prompts"]],
    ]
    if synthesis["in_class_additions"]:
        recall_lines += ["", "## What class added", *[f"- {item}" for item in synthesis["in_class_additions"]]]
    recall_text = "\n".join(recall_lines)
    summary_specs = [
        ("logic", 0, logic_text, "5"),
        ("distinctions", summary_width + summary_gap, distinction_text, "1"),
        ("recall", (summary_width + summary_gap) * 2, recall_text, "2"),
    ]
    summary_nodes = []
    for key, x, text, color in summary_specs:
        node_id = stable_id(key, note_relative)
        summary_nodes.append(
            {
                "id": node_id,
                "type": "text",
                "x": x,
                "y": synthesis_y,
                "width": summary_width,
                "height": render_height(
                    render_metrics,
                    node_id,
                    text,
                    summary_width,
                    text_height(text, summary_width, 260, 700),
                ),
                "text": text,
                "color": color,
            }
        )

    relation_color = {
        "supports": "4", "example-of": "4", "causes": "6", "leads-to": "6",
        "contrasts": "1", "limits": "1", "qualifies": "1", "requires": "2",
    }
    for relation in model["relations"]:
        source = node_by_key[relation["from"]]
        target = node_by_key[relation["to"]]
        from_side, to_side = edge_sides(source, target)
        edges.append(
            {
                "id": stable_id(
                    "edge",
                    f"{note_relative}:{relation['from']}->{relation['to']}:{relation['type']}",
                ),
                "fromNode": source["id"],
                "fromSide": from_side,
                "toNode": target["id"],
                "toSide": to_side,
                "toEnd": "arrow",
                "label": relation["label"],
                "color": relation_color.get(relation["type"], "5"),
            }
        )

    return {
        "nodes": group_nodes + [overview_node, file_node] + content_nodes + summary_nodes,
        "edges": edges,
    }


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
    parser.add_argument("--model", required=True, type=Path, help="Agent-authored staging recall-model JSON")
    parser.add_argument("--render-metrics", type=Path, help="First-pass Obsidian DOM measurements")
    parser.add_argument("--assets-dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if not args.model.is_file():
            raise CanvasBuildError(f"recall model not found: {args.model}")
        model = json.loads(args.model.read_text(encoding="utf-8"))
        render_metrics = None
        if args.render_metrics is not None:
            if not args.render_metrics.is_file():
                raise CanvasBuildError(f"render metrics not found: {args.render_metrics}")
            render_metrics = json.loads(args.render_metrics.read_text(encoding="utf-8"))
        canvas = build_canvas(
            args.note,
            args.vault_root,
            args.profile,
            model,
            args.assets_dir,
            render_metrics,
        )
        if args.output.resolve().parent != args.note.resolve().parent:
            raise CanvasBuildError("Canvas output must be beside the complete Markdown note")
        if args.output.exists() and not args.overwrite:
            raise CanvasBuildError("Canvas output already exists; use --overwrite only after preserving user edits")
        write_atomic(args.output, canvas)
    except (OSError, json.JSONDecodeError, CanvasBuildError) as exc:
        print(f"build-canvas error: {exc}", file=sys.stderr)
        return 1
    print(f"knowledge-recall Canvas written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
