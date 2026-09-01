#!/usr/bin/env python3
"""Verify that a slide-layout refinement preserves page-local content and order."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path


PAGE_MARKER = re.compile(r"(?m)^[ \t]*<!--\s*source-page:\s*(\d+)\s*-->[ \t]*$")
OBSIDIAN_EMBED = re.compile(r"!\[\[([^\]]+)\]\]")
MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
WIKILINK = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")
MARKDOWN_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
BULLET_GLYPH = re.compile(r"(?m)^\s*[▶►▪•●◦‣]\s*")
CALLOUT = re.compile(r"(?m)^\s*>\s*\[![^\]]+\]")
HORIZONTAL_RULE = re.compile(r"(?m)^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")


class RefinementError(RuntimeError):
    pass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise RefinementError("frontmatter is not closed")
    end += 5
    return text[:end], text[end:]


def split_pages(body: str) -> tuple[list[str], list[str], list[int | None]]:
    matches = list(PAGE_MARKER.finditer(body))
    marker_texts = [match.group(0) for match in matches]
    page_ids: list[int | None] = [None]
    segments = [body[: matches[0].start()] if matches else body]
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        segments.append(body[start:end])
        page_ids.append(int(match.group(1)))
    return marker_texts, segments, page_ids


def extract_assets(text: str) -> tuple[str, list[str]]:
    assets = []

    def obsidian(match):
        target = match.group(1).split("|", 1)[0].strip()
        assets.append(target)
        return " "

    def markdown(match):
        assets.append(match.group(1).strip())
        return " "

    text = OBSIDIAN_EMBED.sub(obsidian, text)
    text = MARKDOWN_IMAGE.sub(markdown, text)
    return text, assets


def extract_links(text: str) -> tuple[str, list[str]]:
    links = []

    def wiki(match):
        raw = match.group(1)
        parts = raw.split("|", 1)
        links.append(parts[0].strip())
        return parts[1].strip() if len(parts) == 2 else parts[0].strip()

    def markdown(match):
        links.append(match.group(2).strip())
        return match.group(1)

    text = WIKILINK.sub(wiki, text)
    text = MARKDOWN_LINK.sub(markdown, text)
    return text, links


def canonical_page(text: str) -> dict:
    without_assets, assets = extract_assets(text)
    without_links, links = extract_links(without_assets)
    value = re.sub(r"<!--(?!\s*source-page:).*?-->", " ", without_links, flags=re.S)
    value = re.sub(r"(?m)^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", value)
    value = re.sub(r"(?m)^\s*>\s?", "", value)
    value = re.sub(r"(?m)^\s*(?:[-+*]|\d+[.)]|[▶►▪•●◦‣])\s+", "", value)
    value = value.replace("|", " ")
    value = re.sub(r"[`*_~=]", "", value)
    tokens = re.findall(r"[\w]+(?:['’.-][\w]+)*|[^\w\s]", value, flags=re.UNICODE)
    return {"tokens": tokens, "assets": assets, "links": links}


def h2_count(text: str) -> int:
    return len(re.findall(r"(?m)^##\s+", text))


def heading_structure_errors(text: str) -> list[str]:
    errors = []
    levels = [len(match.group(1)) for match in re.finditer(r"(?m)^(#{1,6})\s+", text)]
    if 1 in levels:
        errors.append("H1 is forbidden inside a slide segment")
    if levels.count(2) > 1:
        errors.append("more than one H2 slide title")
    if any(level > 4 for level in levels):
        errors.append("H5/H6 is too deep for slide layout")
    seen_h3 = False
    for level in levels:
        if level == 3:
            seen_h3 = True
        elif level == 2:
            seen_h3 = False
        elif level == 4 and not seen_h3:
            errors.append("H4 appears without a preceding H3 region")
            break
    return errors


def validate_refinement(base: str, candidate: str) -> dict:
    errors = []
    if "lecture-layer:" in base or "lecture-layer:" in candidate:
        errors.append("layout refinement is forbidden after student/teacher layers exist")

    base_frontmatter, base_body = split_frontmatter(base)
    candidate_frontmatter, candidate_body = split_frontmatter(candidate)
    if base_frontmatter != candidate_frontmatter:
        errors.append("frontmatter changed")

    base_markers, base_pages, base_ids = split_pages(base_body)
    candidate_markers, candidate_pages, candidate_ids = split_pages(candidate_body)
    if base_markers != candidate_markers or base_ids != candidate_ids:
        errors.append("source-page markers changed or reordered")
    if len(base_pages) != len(candidate_pages):
        errors.append("page segment count changed")

    page_results = []
    for index, (base_page, candidate_page) in enumerate(zip(base_pages, candidate_pages)):
        page_id = base_ids[index]
        base_canonical = canonical_page(base_page)
        candidate_canonical = canonical_page(candidate_page)
        page_errors = []
        if base_canonical["tokens"] != candidate_canonical["tokens"]:
            page_errors.append("visible text tokens changed or reordered")
        if collections.Counter(base_canonical["assets"]) != collections.Counter(candidate_canonical["assets"]):
            page_errors.append("asset set changed on this page")
        if collections.Counter(base_canonical["links"]) != collections.Counter(candidate_canonical["links"]):
            page_errors.append("link destinations changed on this page")
        if page_id is None:
            if base_page != candidate_page:
                page_errors.append("document preamble changed")
        else:
            if BULLET_GLYPH.search(candidate_page):
                page_errors.append("decorative bullet glyph remains in candidate")
            page_errors.extend(heading_structure_errors(candidate_page))
            if CALLOUT.search(candidate_page):
                page_errors.append("callout syntax introduces a generated visible label")
            without_comments = re.sub(r"<!--.*?-->", "", candidate_page, flags=re.S)
            if re.search(r"</?[A-Za-z][^>]*>", without_comments):
                page_errors.append("raw HTML is forbidden; use native Markdown")
            if len(HORIZONTAL_RULE.findall(candidate_page)) > len(HORIZONTAL_RULE.findall(base_page)):
                page_errors.append("new horizontal rule would compete with source-page separation")
        if page_errors:
            errors.extend(f"page {page_id if page_id is not None else 'preamble'}: {item}" for item in page_errors)
        page_results.append(
            {
                "page": page_id,
                "changed": base_page != candidate_page,
                "base_h2": h2_count(base_page),
                "candidate_h2": h2_count(candidate_page),
                "base_assets": base_canonical["assets"],
                "candidate_assets": candidate_canonical["assets"],
                "asset_order_changed": base_canonical["assets"] != candidate_canonical["assets"],
                "errors": page_errors,
            }
        )

    return {
        "schema_version": 1,
        "valid": not errors,
        "base_sha256": sha256_text(base),
        "candidate_sha256": sha256_text(candidate),
        "page_markers": base_ids[1:],
        "pages_changed": sum(1 for page in page_results if page["changed"]),
        "base_bullet_glyphs": len(BULLET_GLYPH.findall(base_body)),
        "candidate_bullet_glyphs": len(BULLET_GLYPH.findall(candidate_body)),
        "pages": page_results,
        "errors": errors,
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
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        base = args.base.read_text(encoding="utf-8")
        candidate = args.candidate.read_text(encoding="utf-8")
        result = validate_refinement(base, candidate)
        result["base"] = str(args.base.resolve())
        result["candidate"] = str(args.candidate.resolve())
        if args.report is not None:
            write_json_atomic(args.report.resolve(), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    except (OSError, UnicodeDecodeError, RefinementError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
