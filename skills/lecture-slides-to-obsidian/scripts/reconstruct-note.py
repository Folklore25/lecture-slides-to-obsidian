#!/usr/bin/env python3
"""Reconstruct complete Obsidian Markdown from MinerU content_list_v2.json."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path


AUX_TYPES = {"page_header", "page_footer", "page_number", "page_aside_text", "page_footnote"}
PROFILE_CHOICES = ("lecture-notes", "policy-document", "paper")
POLICY_ITEM_PARENT = re.compile(r"(?:category|advice|requirement|rule|obligation|principle|conduct)", re.I)
OVERVIEW_PARENT = re.compile(r"(?:overview|contents|index|summary)", re.I)
POLICY_SECTION = re.compile(r"^(?:overview|category\b|advice\b|scope\b|definitions?\b|history\b|enforcement\b|exceptions?\b|requirements?\b|principles?\b)", re.I)
NUMBERED_SHORT = re.compile(r"^\s*(\d{1,3}[.)]\s+\S.+?)\s*$")


class ReconstructionError(RuntimeError):
    pass


def flatten(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "".join(flatten(item) for item in value)
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
                return flatten(value[key])
        return "".join(flatten(item) for item in value.values())
    return ""


def find_asset_path(value) -> str | None:
    if isinstance(value, dict):
        for key in ("img_path", "image_path", "table_path", "chart_path"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate
        for item in value.values():
            found = find_asset_path(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_asset_path(item)
            if found:
                return found
    return None


def yaml_scalar(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def page_blocks(page) -> list[dict]:
    if isinstance(page, list):
        return [item for item in page if isinstance(item, dict)]
    if isinstance(page, dict):
        for key in ("blocks", "content", "items"):
            if isinstance(page.get(key), list):
                return [item for item in page[key] if isinstance(item, dict)]
        raise ReconstructionError("each normalized page must be an array or page object with blocks")


def render_block(block: dict, profile: str, state: dict, inventory: dict) -> str | None:
    block_type = block.get("type")
    content = block.get("content", {})
    if block_type in AUX_TYPES:
        inventory[block_type] += 1
        inventory["auxiliary_pages"].setdefault(block_type, []).append(state["page_number"])
        return None

    text = flatten(content).strip()
    if block_type == "title":
        level = content.get("level", 1) if isinstance(content, dict) else 1
        level = level if isinstance(level, int) and level > 0 else 1
        if profile == "policy-document":
            if POLICY_SECTION.search(text):
                state["current_h2"] = text
                return f"## {text}" if text else None
            if NUMBERED_SHORT.match(text) and len(text) <= 180:
                return f"### {text}"
        markdown_level = min(level + 1, 6)
        if markdown_level == 2:
            state["current_h2"] = text
        return f"{'#' * markdown_level} {text}" if text else None

    if block_type == "paragraph":
        if not text:
            return None
        match = NUMBERED_SHORT.match(text)
        if profile == "policy-document" and match and len(text) <= 180:
            parent = state.get("current_h2", "")
            if OVERVIEW_PARENT.search(parent):
                return f"**{text}**"
            if POLICY_ITEM_PARENT.search(parent):
                return f"### {text}"
        return text

    if block_type in {"list", "index"}:
        items = content.get("list_items", []) if isinstance(content, dict) else []
        rendered = [flatten(item).strip() for item in items]
        return "\n".join(f"- {item}" for item in rendered if item) or text or None

    if block_type == "equation_interline":
        inventory["equations"] += 1
        return f"$$\n{text}\n$$" if text else None

    if block_type in {"image", "chart", "table"}:
        key = "tables" if block_type == "table" else "figures_images"
        inventory[key] += 1
        asset = find_asset_path(block)
        caption = text
        parts: list[str] = []
        if asset:
            parts.append(f"![[assets/{Path(asset).name}]]")
        if caption:
            parts.append(caption)
        return "\n\n".join(parts) or None

    if block_type in {"code", "algorithm"}:
        language = content.get("code_language", "") if isinstance(content, dict) else ""
        return f"```{language}\n{text}\n```" if text else None

    return text or None


def reconstruct(pages: list, metadata: dict, profile: str) -> tuple[str, dict]:
    if not isinstance(pages, list) or not pages:
        raise ReconstructionError("page-group input must be a non-empty top-level array")
    inventory = {
        "pages": len(pages),
        "figures_images": 0,
        "tables": 0,
        "equations": 0,
        "fallback_pages": 0,
        "page_header": 0,
        "page_footer": 0,
        "page_number": 0,
        "page_aside_text": 0,
        "page_footnote": 0,
        "auxiliary_pages": {},
    }
    frontmatter = [
        "---",
        "type: course-material",
        f"course: {yaml_scalar(metadata['course'])}",
        f"title: {yaml_scalar(metadata['title'])}",
        f"source_filename: {yaml_scalar(Path(metadata['source_filename']).name)}",
        f"source_format: {yaml_scalar(Path(metadata['source_filename']).suffix.lower().lstrip('.'))}",
        f"source_sha256: {yaml_scalar(metadata['source_sha256'])}",
        f"source_pages: {len(pages)}",
        f"conversion_profile: {profile}",
        f"mineru_model: {yaml_scalar(metadata['mineru_model'])}",
        f"status: {yaml_scalar(metadata['status'])}",
        "---",
        "",
        f"# {metadata['title']}",
    ]
    lines = frontmatter
    state = {"current_h2": "", "page_number": 0}
    for index, page in enumerate(pages):
        state["page_number"] = index + 1
        rendered: list[str] = []
        for block in page_blocks(page):
            value = render_block(block, profile, state, inventory)
            if value:
                rendered.append(value)
        if rendered:
            lines += ["", f"<!-- source-page: {index + 1} -->", ""]
            lines += [item for value in rendered for item in (value, "")]
            if lines[-1] == "":
                lines.pop()
    if profile == "lecture-notes":
        lines += ["", "## In-class notes"]
    context = {
        "page_count_source": "normalized page-group length",
        "inventory": inventory,
        "profile": profile,
    }
    return "\n".join(lines).rstrip() + "\n", context


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-groups", "--content-list-v2", dest="page_groups", required=True, type=Path)
    parser.add_argument("--profile", required=True, choices=PROFILE_CHOICES)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--context-output", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--course", required=True)
    parser.add_argument("--source-filename", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--mineru-model", default="vlm")
    parser.add_argument("--status", default="pre-class")
    args = parser.parse_args()
    try:
        pages = json.loads(args.page_groups.read_text(encoding="utf-8"))
        note, context = reconstruct(
            pages,
            {
                "title": args.title,
                "course": args.course,
                "source_filename": args.source_filename,
                "source_sha256": args.source_sha256,
                "mineru_model": args.mineru_model,
                "status": args.status,
            },
            args.profile,
        )
        write_atomic(args.output, note)
        write_atomic(args.context_output, json.dumps(context, ensure_ascii=False, indent=2) + "\n")
    except (OSError, json.JSONDecodeError, ReconstructionError) as exc:
        print(f"reconstruct-note error: {exc}", file=sys.stderr)
        return 1
    print(f"complete Markdown written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
