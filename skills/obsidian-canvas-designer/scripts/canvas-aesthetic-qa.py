#!/usr/bin/env python3
"""Score deterministic visual readability rules for an Obsidian knowledge Canvas."""

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


ROLE = re.compile(r"<!--\s*recall-map:\s*([a-z-]+)\s*-->")
KIND = re.compile(r"<!--\s*recall-kind:\s*([a-z-]+)\s*-->")
EXPECTED_COLORS = {
    "boundary": "1", "misconception": "1", "limitation": "1", "exception": "1",
    "rule": "2",
    "foundation": "3", "concept": "3",
    "example": "4", "application": "4", "evidence": "4", "finding": "4",
    "mechanism": "5", "process": "5", "method": "5",
    "claim": "6", "decision": "6", "comparison": "6",
}


class AestheticQaError(RuntimeError):
    pass


def write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def center(node: dict) -> tuple[float, float]:
    return node["x"] + node["width"] / 2, node["y"] + node["height"] / 2


def contains(group: dict, node: dict) -> bool:
    return (
        node["x"] >= group["x"]
        and node["y"] >= group["y"]
        and node["x"] + node["width"] <= group["x"] + group["width"]
        and node["y"] + node["height"] <= group["y"] + group["height"]
    )


def orientation(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def proper_intersection(a, b, c, d) -> bool:
    o1, o2 = orientation(a, b, c), orientation(a, b, d)
    o3, o4 = orientation(c, d, a), orientation(c, d, b)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def segment_intersects_rect(a, b, rect: dict) -> bool:
    left, top = rect["x"], rect["y"]
    right, bottom = left + rect["width"], top + rect["height"]
    if left < a[0] < right and top < a[1] < bottom:
        return True
    if left < b[0] < right and top < b[1] < bottom:
        return True
    corners = [(left, top), (right, top), (right, bottom), (left, bottom)]
    return any(
        proper_intersection(a, b, corners[index], corners[(index + 1) % 4])
        for index in range(4)
    )


def visible_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("<!--")
    ]


def score_canvas(data: dict) -> dict:
    nodes = data.get("nodes")
    edges = data.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise AestheticQaError("Canvas must contain nodes and edges arrays")
    by_id = {node.get("id"): node for node in nodes if isinstance(node, dict)}
    groups = [node for node in nodes if node.get("type") == "group"]
    concepts = []
    hard_errors: list[str] = []
    review_items: list[str] = []
    deductions = 0

    for node in nodes:
        if node.get("type") != "text" or not isinstance(node.get("text"), str):
            continue
        role_match = ROLE.search(node["text"])
        if not role_match or role_match.group(1) != "concept":
            continue
        concepts.append(node)
        lines = visible_lines(node["text"])
        title = next((line[4:] for line in lines if line.startswith("### ")), None)
        if title is None or any(line.startswith("## ") for line in lines):
            hard_errors.append(f"concept {node.get('id')} must use one H3 title")
        elif len(title) > (30 if re.search(r"[\u3400-\u9fff]", title) else 60):
            hard_errors.append(f"concept {node.get('id')} title is too long")
        if "Recall cue:" in node["text"] or "回忆提示" in node["text"]:
            hard_errors.append(f"concept {node.get('id')} repeats a recall cue instead of using the shared recall zone")
        if not re.search(r"\[\[[^\]]+\|Source p\.\d+\]\]", node["text"]):
            hard_errors.append(f"concept {node.get('id')} lacks a compact Source p.N link")
        if len(lines) > 5 or len(node["text"]) > 600:
            hard_errors.append(f"concept {node.get('id')} exceeds the card density budget")
        if node.get("width") != 440:
            hard_errors.append(f"concept {node.get('id')} must use the 440px reading width")
        kind_match = KIND.search(node["text"])
        if not kind_match:
            hard_errors.append(f"concept {node.get('id')} lacks recall-kind metadata")
        else:
            expected = EXPECTED_COLORS.get(kind_match.group(1))
            if expected and node.get("color") != expected:
                hard_errors.append(f"concept {node.get('id')} color does not match semantic kind")

    for group in groups:
        label = group.get("label", "")
        if len(label) > 80:
            hard_errors.append(f"group {group.get('id')} label is too long")
        members = [node for node in concepts if contains(group, node)]
        if not members:
            hard_errors.append(f"group {group.get('id')} contains no concept cards")
            continue
        member_colors: dict[str, int] = {}
        for member in members:
            color = member.get("color")
            member_colors[color] = member_colors.get(color, 0) + 1
        dominant = sorted(member_colors, key=lambda color: (-member_colors[color], color))[0]
        if group.get("color") != dominant:
            hard_errors.append(f"group {group.get('id')} color is not its dominant semantic color")
        aligned = sorted(members, key=lambda node: node["y"])
        for first, second in zip(aligned, aligned[1:]):
            if abs(first["x"] - second["x"]) <= 10:
                gap = second["y"] - (first["y"] + first["height"])
                if gap < 60:
                    hard_errors.append(f"group {group.get('id')} has a vertical card gap below 60px")
                elif gap > 100:
                    deductions += 3
                    review_items.append(f"group {group.get('id')} has an excessive {gap}px vertical gap")

    semantic_edges = [
        edge for edge in edges
        if edge.get("fromNode") in by_id and edge.get("toNode") in by_id
        and by_id[edge["fromNode"]] in concepts and by_id[edge["toNode"]] in concepts
    ]
    segments = []
    for edge in semantic_edges:
        label = edge.get("label", "")
        if not isinstance(label, str) or not 2 <= len(label) <= 42:
            hard_errors.append(f"edge {edge.get('id')} label is missing or too long")
        source = by_id[edge["fromNode"]]
        target = by_id[edge["toNode"]]
        segment = (center(source), center(target), edge)
        segments.append(segment)
        for node in concepts:
            if node.get("id") in {edge.get("fromNode"), edge.get("toNode")}:
                continue
            if segment_intersects_rect(segment[0], segment[1], node):
                hard_errors.append(f"edge {edge.get('id')} passes through unrelated concept {node.get('id')}")

    crossings = 0
    for index, first in enumerate(segments):
        for second in segments[index + 1 :]:
            endpoints_a = {first[2].get("fromNode"), first[2].get("toNode")}
            endpoints_b = {second[2].get("fromNode"), second[2].get("toNode")}
            if endpoints_a & endpoints_b:
                continue
            if proper_intersection(first[0], first[1], second[0], second[1]):
                crossings += 1
    crossing_limit = max(2, math.floor(len(semantic_edges) * 0.1))
    if crossings > crossing_limit:
        hard_errors.append(f"semantic edge crossings {crossings} exceed limit {crossing_limit}")
    deductions += min(20, crossings * 4)

    visible_colors = {node.get("color") for node in concepts if node.get("color")}
    if len(visible_colors) > 5:
        deductions += 5
        review_items.append("concept palette uses more than five semantic colors")

    score = max(0, 100 - deductions - min(60, len(hard_errors) * 10))
    return {
        "schema_version": 1,
        "score": score,
        "minimum_score": 85,
        "valid": not hard_errors and score >= 85,
        "concept_nodes": len(concepts),
        "semantic_edges": len(semantic_edges),
        "edge_crossings": crossings,
        "hard_errors": hard_errors,
        "review_items": review_items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canvas", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.canvas.read_text(encoding="utf-8"))
        result = score_canvas(data)
        result["canvas"] = str(args.canvas.resolve())
        result["canvas_sha256"] = sha256_file(args.canvas)
        if args.output is not None:
            write_json_atomic(args.output.resolve(), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    except (OSError, json.JSONDecodeError, AestheticQaError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
