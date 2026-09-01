#!/usr/bin/env python3
"""Validate an in-place slide-layout refinement and roll it back on failure."""

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
    value = re.sub(r"(?m)^\s*(?:\\-|[-+*]|\d+[.)]|[▶►▪•●◦‣])\s+", "", value)
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


def validate_refinement(snapshot: str, refined: str) -> dict:
    errors = []
    if "lecture-layer:" in snapshot or "lecture-layer:" in refined:
        errors.append("layout refinement is forbidden after student/teacher layers exist")

    snapshot_frontmatter, snapshot_body = split_frontmatter(snapshot)
    refined_frontmatter, refined_body = split_frontmatter(refined)
    if snapshot_frontmatter != refined_frontmatter:
        errors.append("frontmatter changed")

    snapshot_markers, snapshot_pages, snapshot_ids = split_pages(snapshot_body)
    refined_markers, refined_pages, refined_ids = split_pages(refined_body)
    if snapshot_markers != refined_markers or snapshot_ids != refined_ids:
        errors.append("source-page markers changed or reordered")
    if len(snapshot_pages) != len(refined_pages):
        errors.append("page segment count changed")

    page_results = []
    for index, (snapshot_page, refined_page) in enumerate(zip(snapshot_pages, refined_pages)):
        page_id = snapshot_ids[index]
        snapshot_canonical = canonical_page(snapshot_page)
        refined_canonical = canonical_page(refined_page)
        page_errors = []
        if snapshot_canonical["tokens"] != refined_canonical["tokens"]:
            page_errors.append("visible text tokens changed or reordered")
        if collections.Counter(snapshot_canonical["assets"]) != collections.Counter(refined_canonical["assets"]):
            page_errors.append("asset set changed on this page")
        if collections.Counter(snapshot_canonical["links"]) != collections.Counter(refined_canonical["links"]):
            page_errors.append("link destinations changed on this page")
        if page_id is None:
            if snapshot_page != refined_page:
                page_errors.append("document preamble changed")
        else:
            if BULLET_GLYPH.search(refined_page):
                page_errors.append("decorative bullet glyph remains in refined Markdown")
            if re.search(r"(?m)^\s*\\-\s+", refined_page):
                page_errors.append("escaped list marker remains in refined Markdown")
            page_errors.extend(heading_structure_errors(refined_page))
            if CALLOUT.search(refined_page):
                page_errors.append("callout syntax introduces a generated visible label")
            without_comments = re.sub(r"<!--.*?-->", "", refined_page, flags=re.S)
            if re.search(r"</?[A-Za-z][^>]*>", without_comments):
                page_errors.append("raw HTML is forbidden; use native Markdown")
            if len(HORIZONTAL_RULE.findall(refined_page)) > len(HORIZONTAL_RULE.findall(snapshot_page)):
                page_errors.append("new horizontal rule would compete with source-page separation")
        if page_errors:
            errors.extend(f"page {page_id if page_id is not None else 'preamble'}: {item}" for item in page_errors)
        page_results.append(
            {
                "page": page_id,
                "changed": snapshot_page != refined_page,
                "snapshot_h2": h2_count(snapshot_page),
                "refined_h2": h2_count(refined_page),
                "snapshot_assets": snapshot_canonical["assets"],
                "refined_assets": refined_canonical["assets"],
                "asset_order_changed": snapshot_canonical["assets"] != refined_canonical["assets"],
                "errors": page_errors,
            }
        )

    return {
        "schema_version": 1,
        "valid": not errors,
        "snapshot_sha256": sha256_text(snapshot),
        "refined_sha256": sha256_text(refined),
        "page_markers": snapshot_ids[1:],
        "pages_changed": sum(1 for page in page_results if page["changed"]),
        "snapshot_bullet_glyphs": len(BULLET_GLYPH.findall(snapshot_body)),
        "refined_bullet_glyphs": len(BULLET_GLYPH.findall(refined_body)),
        "snapshot_escaped_list_markers": len(re.findall(r"(?m)^\s*\\-\s+", snapshot_body)),
        "refined_escaped_list_markers": len(re.findall(r"(?m)^\s*\\-\s+", refined_body)),
        "pages": page_results,
        "errors": errors,
    }


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def restore_in_place(path: Path, content: bytes) -> None:
    # Do not create a sibling rollback file in the vault. The byte-exact snapshot
    # already exists outside it, so restore the one authorized target directly.
    with path.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


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
    parser.add_argument("--snapshot", required=True, type=Path, help="Byte-exact pre-edit note outside the vault")
    parser.add_argument("--target", required=True, type=Path, help="Overwritten Markdown note inside the vault")
    parser.add_argument("--vault-root", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path, help="Temporary validation report outside the vault")
    args = parser.parse_args()
    snapshot_path = args.snapshot.resolve()
    target_path = args.target.resolve()
    vault_root = args.vault_root.resolve()
    report_path = args.report.resolve()
    snapshot_bytes = None
    try:
        if args.snapshot.is_symlink() or args.target.is_symlink() or args.report.is_symlink():
            raise RefinementError("snapshot, target, and report must not be symlinks")
        if not inside(target_path, vault_root):
            raise RefinementError("target Markdown must be inside --vault-root")
        relative_target = target_path.relative_to(vault_root)
        if any(part.startswith(".") for part in relative_target.parts):
            raise RefinementError("target Markdown must not be inside a dot-prefixed vault path")
        if inside(snapshot_path, vault_root) or inside(report_path, vault_root):
            raise RefinementError("snapshot and report must be outside the Obsidian vault")
        if snapshot_path == target_path or report_path in (snapshot_path, target_path):
            raise RefinementError("snapshot, target, and report paths must be distinct")
        snapshot_bytes = snapshot_path.read_bytes()
        target_bytes = target_path.read_bytes()
        snapshot = snapshot_bytes.decode("utf-8")
        refined = target_bytes.decode("utf-8")
        result = validate_refinement(snapshot, refined)
        result["snapshot"] = str(snapshot_path)
        result["target"] = str(target_path)
        result["report"] = str(report_path)
        result["restored"] = False
        if not result["valid"]:
            restore_in_place(target_path, snapshot_bytes)
            result["restored"] = True
            result["restored_sha256"] = hashlib.sha256(target_path.read_bytes()).hexdigest()
        write_json_atomic(report_path, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    except (OSError, UnicodeDecodeError, RefinementError) as exc:
        restored = False
        restore_error = None
        if snapshot_bytes is not None and target_path.is_file():
            try:
                restore_in_place(target_path, snapshot_bytes)
                restored = True
            except OSError as rollback_exc:
                restore_error = str(rollback_exc)
        print(json.dumps({"valid": False, "error": str(exc), "restored": restored, "restore_error": restore_error}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
