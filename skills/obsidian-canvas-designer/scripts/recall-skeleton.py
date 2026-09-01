#!/usr/bin/env python3
"""Inspect note headings and create a provenance-complete recall-model authoring draft."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path


PROFILES = {"lecture-notes", "policy-document", "paper"}
PAGE_MARKER = re.compile(r"<!--\s*source-page:\s*(\d+)\s*-->")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class SkeletonError(RuntimeError):
    pass


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if match:
            result[match.group(1)] = match.group(2).strip("\"'")
    return result


def inspect_note(text: str) -> dict:
    frontmatter = parse_frontmatter(text)
    current_page: int | None = None
    h1_title: str | None = None
    h2_sections = []
    h3_candidates = []
    current_h2: str | None = None
    hard_errors = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        marker = PAGE_MARKER.fullmatch(line.strip())
        if marker:
            current_page = int(marker.group(1))
            continue
        heading = HEADING.match(line)
        if not heading:
            continue
        level = len(heading.group(1))
        title = heading.group(2).strip()
        if level == 1 and h1_title is None:
            h1_title = title
        elif level == 2:
            current_h2 = title
            h2_sections.append({"heading": title, "source_page": current_page, "line": line_number})
        elif level == 3:
            h3_candidates.append(
                {
                    "heading": title,
                    "source_page": current_page,
                    "line": line_number,
                    "parent_h2": current_h2,
                }
            )

    if not h2_sections:
        hard_errors.append(
            "No H2 sections found. Canvas concepts require exact ## H2 anchors; review H3 candidates outside this skill."
        )
    missing_pages = [item for item in h2_sections if item["source_page"] is None]
    if missing_pages:
        hard_errors.append(
            "H2 sections without a preceding source-page marker: "
            + ", ".join(f"{item['heading']} (line {item['line']})" for item in missing_pages)
        )
    seen: set[tuple[str, int | None]] = set()
    duplicates = []
    for item in h2_sections:
        key = (item["heading"], item["source_page"])
        if key in seen:
            duplicates.append(item)
        seen.add(key)
    if duplicates:
        hard_errors.append(
            "Duplicate H2 heading/page anchors cannot be addressed uniquely: "
            + ", ".join(f"{item['heading']} (page {item['source_page']})" for item in duplicates)
        )

    try:
        source_pages = int(frontmatter.get("source_pages", "0"))
    except ValueError:
        source_pages = 0
    out_of_range = [
        item for item in h2_sections
        if item["source_page"] is not None and source_pages > 0 and item["source_page"] > source_pages
    ]
    if out_of_range:
        hard_errors.append("H2 source-page provenance exceeds frontmatter source_pages")

    return {
        "frontmatter": frontmatter,
        "title": h1_title or frontmatter.get("title") or "",
        "source_pages": source_pages,
        "h2_sections": h2_sections,
        "h3_review_candidates": h3_candidates,
        "hard_errors": hard_errors,
    }


def create_skeleton(inspection: dict, profile: str, mode: str) -> dict:
    coverage = [
        {
            "source_heading": item["heading"],
            "source_page": item["source_page"],
            "concepts": [],
            "omission_reason": "",
        }
        for item in inspection["h2_sections"]
    ]
    return {
        "schema_version": 1,
        "draft_status": "authoring-required",
        "profile": profile,
        "mode": mode,
        "title": inspection["title"],
        "orientation": {"central_question": "", "one_sentence_answer": "", "takeaways": []},
        "groups": [],
        "concepts": [],
        "relations": [],
        "coverage": coverage,
        "synthesis": {
            "logic_chain": [],
            "distinctions": [],
            "recall_prompts": [],
            "in_class_additions": [],
        },
        "asset_links": [],
        "_authoring": {
            "h2_count": len(inspection["h2_sections"]),
            "h3_review_candidates": inspection["h3_review_candidates"],
            "hard_errors": inspection["hard_errors"],
            "instructions": [
                "Fill semantic fields; this draft is intentionally not build-valid.",
                "Map or explain every coverage row.",
                "Do not edit or promote note headings inside the Canvas skill.",
                "Remove _authoring and set draft_status to ready after review.",
            ],
        },
    }


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--note", required=True, type=Path)
    parser.add_argument("--profile", choices=sorted(PROFILES))
    parser.add_argument("--mode", choices=("pre-class", "post-class"), default="pre-class")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        text = args.note.read_text(encoding="utf-8")
        inspection = inspect_note(text)
        profile = args.profile or inspection["frontmatter"].get("conversion_profile")
        if profile not in PROFILES:
            raise SkeletonError("profile is missing or unsupported; pass --profile")
        skeleton = create_skeleton(inspection, profile, args.mode)
        if args.output is not None:
            write_json_atomic(args.output.resolve(), skeleton)
            response = {
                "draft": str(args.output.resolve()),
                "h2_count": len(inspection["h2_sections"]),
                "h3_review_candidates": inspection["h3_review_candidates"],
                "hard_errors": inspection["hard_errors"],
                "next": "fill semantic fields, remove _authoring, set draft_status=ready",
            }
        else:
            response = skeleton
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0 if not inspection["hard_errors"] else 1
    except (OSError, UnicodeDecodeError, SkeletonError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
