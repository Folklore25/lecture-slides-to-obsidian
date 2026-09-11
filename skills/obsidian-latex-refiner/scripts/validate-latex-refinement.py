#!/usr/bin/env python3
"""Validate a page-local LaTeX/math normalization and roll it back on failure."""

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
CALLOUT_HEADER = re.compile(r"(?m)^[ \t]*>[ \t]*\[![^\]\r\n]+\][+-]?(?:[ \t]+[^\r\n]*)?$")
CONVERSION_LAYER_MARKER = re.compile(r"(?m)^[ \t]*<!--\s*conversion-layer:[^>\r\n]+-->[ \t]*$")
CODE_FENCE = re.compile(r"(?ms)^[ \t]*(?:\x60\x60\x60|~~~)[^\n]*\n.*?^[ \t]*(?:\x60\x60\x60|~~~)[ \t]*$")
INLINE_CODE = re.compile(r"\x60[^\x60\n]*\x60")
PLACEHOLDER = "\x00LATEX-VERBATIM-{}\x00"
CJK = re.compile(r"[\u2e80-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]")

EQUATION_ENVS = {"equation", "equation*", "displaymath", "math"}
ALIGN_ENVS = {"align", "align*", "aligned", "eqnarray", "eqnarray*", "flalign", "flalign*", "alignat", "alignat*", "split"}
GATHER_ENVS = {"gather", "gather*", "gathered", "multline", "multline*"}
MATRIX_ENVS = {"cases", "array", "matrix", "pmatrix", "bmatrix", "Bmatrix", "vmatrix", "Vmatrix", "smallmatrix", "subarray"}
MATH_ENVS = EQUATION_ENVS | ALIGN_ENVS | GATHER_ENVS | MATRIX_ENVS

LABEL = re.compile(r"\\label\s*\{[^{}]*\}")
NONUMBER = re.compile(r"\\(?:nonumber|notag)\b")
TEXT_WRAP_CJK = re.compile(r"\\(?:text|mbox|textrm|textnormal)\s*\{([^{}]*[^\x00-\x7F][^{}]*)\}")
ENV_TOKEN = re.compile(r"\\(?:begin|end)\{([A-Za-z*]+)\}")
TOKEN = re.compile(r"\\[A-Za-z]+|\\.|[^\s]")


class RefinementError(RuntimeError):
    pass


HANDLED_ERRORS = (OSError, UnicodeDecodeError, RefinementError)


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


def marker_number(match: re.Match) -> int:
    try:
        return int(match.group(1))
    except ValueError as exc:
        raise RefinementError("source-page marker number is invalid") from exc


def split_pages(body: str) -> tuple[list[str], list[str], list[int | None]]:
    matches = list(PAGE_MARKER.finditer(body))
    marker_texts = [match.group(0) for match in matches]
    page_ids: list[int | None] = [None]
    segments = [body[: matches[0].start()] if matches else body]
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        segments.append(body[start:end])
        page_ids.append(marker_number(match))
    return marker_texts, segments, page_ids


def mask_verbatim(text: str) -> tuple[str, list[str]]:
    blocks: list[str] = []

    def replace(match: re.Match) -> str:
        key = PLACEHOLDER.format(len(blocks))
        blocks.append(match.group(0))
        return key

    text = CODE_FENCE.sub(replace, text)
    text = INLINE_CODE.sub(replace, text)
    return text, blocks


def unmask_verbatim(text: str, blocks: list[str]) -> str:
    for index, block in enumerate(blocks):
        text = text.replace(PLACEHOLDER.format(index), block)
    return text


def find_math_spans(text: str) -> list[dict]:
    spans: list[dict] = []
    index = 0
    length = len(text)
    while index < length:
        if text.startswith("$$", index):
            end = text.find("$$", index + 2)
            if end < 0:
                return spans
            spans.append({"start": index, "end": end + 2, "kind": "display", "env": None, "inner": text[index + 2:end], "raw": text[index:end + 2]})
            index = end + 2
            continue
        if text.startswith("\\[", index):
            end = text.find("\\]", index + 2)
            if end < 0:
                return spans
            spans.append({"start": index, "end": end + 2, "kind": "display", "env": None, "inner": text[index + 2:end], "raw": text[index:end + 2]})
            index = end + 2
            continue
        if text.startswith("\\(", index):
            end = text.find("\\)", index + 2)
            if end < 0:
                return spans
            spans.append({"start": index, "end": end + 2, "kind": "inline", "env": None, "inner": text[index + 2:end], "raw": text[index:end + 2]})
            index = end + 2
            continue
        if text.startswith("\\begin{", index):
            close = text.find("}", index + 7)
            if close > 0:
                env = text[index + 7:close]
                if env in MATH_ENVS:
                    end_tag = "\\end{" + env + "}"
                    end = text.find(end_tag, close)
                    if end < 0:
                        index += 1
                        continue
                    kind = "inline" if env == "math" else "display"
                    spans.append({"start": index, "end": end + len(end_tag), "kind": kind, "env": env, "inner": text[close + 1:end], "raw": text[index:end + len(end_tag)]})
                    index = end + len(end_tag)
                    continue
        if text[index] == "\\" and index + 1 < length and text[index + 1] == "$":
            index += 2
            continue
        if text[index] == "$":
            cursor = index + 1
            closing = -1
            while cursor < length:
                if text[cursor] == "\\":
                    cursor += 2
                    continue
                if text[cursor] == "\n" and text.startswith("\n\n", cursor):
                    break
                if text[cursor] == "$":
                    closing = cursor
                    break
                cursor += 1
            if closing > index + 1:
                inner = text[index + 1:closing]
                if inner.strip() == inner:
                    spans.append({"start": index, "end": closing + 1, "kind": "inline", "env": None, "inner": inner, "raw": text[index:closing + 1]})
                    index = closing + 1
                    continue
            index += 1
            continue
        index += 1
    return spans


def text_without_math(text: str) -> str:
    masked, blocks = mask_verbatim(text)
    spans = find_math_spans(masked)
    parts: list[str] = []
    cursor = 0
    for span in spans:
        parts.append(masked[cursor:span["start"]])
        cursor = span["end"]
    parts.append(masked[cursor:])
    return unmask_verbatim("".join(parts), blocks)


def canonical_math(span: dict) -> tuple[str, list[str]]:
    raw = span["raw"]
    if raw.startswith("$$") or raw.startswith("\\[") or raw.startswith("\\("):
        inner = raw[2:-2]
    elif raw.startswith("$"):
        inner = raw[1:-1]
    else:
        inner = raw
    inner = LABEL.sub("", inner)
    inner = NONUMBER.sub("", inner)
    inner = TEXT_WRAP_CJK.sub(r"\1", inner)

    def environment(match: re.Match) -> str:
        env = match.group(1)
        if env in EQUATION_ENVS:
            return ""
        if env in ALIGN_ENVS:
            return "ALIGN"
        if env in GATHER_ENVS:
            return "GATHER"
        return env

    inner = ENV_TOKEN.sub(environment, inner)
    inner = re.sub(r"\s+", "", inner)
    tokens = TOKEN.findall(inner)
    display = span["kind"] == "display" or (span["kind"] == "inline" and "\n" in span["inner"])
    return ("D" if display else "I", tokens)


def extract_assets(text: str) -> tuple[str, list[str]]:
    assets: list[str] = []

    def obsidian(match: re.Match) -> str:
        assets.append(match.group(1).split("|", 1)[0].strip())
        return " "

    def markdown(match: re.Match) -> str:
        assets.append(match.group(1).strip())
        return " "

    text = OBSIDIAN_EMBED.sub(obsidian, text)
    text = MARKDOWN_IMAGE.sub(markdown, text)
    return text, assets


def extract_links(text: str) -> tuple[str, list[str]]:
    links: list[str] = []

    def wiki(match: re.Match) -> str:
        parts = match.group(1).split("|", 1)
        links.append(parts[0].strip())
        return parts[1].strip() if len(parts) == 2 else parts[0].strip()

    def markdown(match: re.Match) -> str:
        links.append(match.group(2).strip())
        return match.group(1)

    text = WIKILINK.sub(wiki, text)
    text = MARKDOWN_LINK.sub(markdown, text)
    return text, links


def canonical_page(text: str) -> dict:
    masked, blocks = mask_verbatim(text)
    spans = find_math_spans(masked)
    parts: list[str] = []
    cursor = 0
    for span in spans:
        parts.append(masked[cursor:span["start"]])
        cursor = span["end"]
    parts.append(masked[cursor:])
    value = unmask_verbatim("".join(parts), blocks)
    value, assets = extract_assets(value)
    value, links = extract_links(value)
    value = re.sub(r"<!--(?!\s*source-page:).*?-->", " ", value, flags=re.S)
    value = re.sub(r"(?m)^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", value)
    value = re.sub(r"(?m)^\s*>\s?", "", value)
    value = re.sub(r"(?m)^\s*(?:\\-|[-+*]|\d+[.)])\s+", "", value)
    value = value.replace("|", " ")
    value = re.sub(r"[\x60*_~=]", "", value)
    tokens = re.findall(r"[\w]+(?:['\u2019.-][\w]+)*|[^\w\s]", value, flags=re.UNICODE)
    return {
        "tokens": tokens,
        "math": [canonical_math(span) for span in spans],
        "assets": assets,
        "links": links,
    }


def validate_refinement(snapshot: str, refined: str) -> dict:
    errors: list[str] = []
    if "lecture-layer:" in snapshot or "lecture-layer:" in refined:
        errors.append("LaTeX refinement is forbidden after student/teacher layers exist")

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
        snapshot_callouts = CALLOUT_HEADER.findall(snapshot_page)
        refined_callouts = CALLOUT_HEADER.findall(refined_page)
        snapshot_conversion = CONVERSION_LAYER_MARKER.findall(snapshot_page)
        refined_conversion = CONVERSION_LAYER_MARKER.findall(refined_page)
        page_errors: list[str] = []
        if snapshot_canonical["tokens"] != refined_canonical["tokens"]:
            page_errors.append("visible non-math text changed or reordered")
        if snapshot_canonical["math"] != refined_canonical["math"]:
            page_errors.append("math content changed, was added, removed, or reordered")
        if collections.Counter(snapshot_canonical["assets"]) != collections.Counter(refined_canonical["assets"]):
            page_errors.append("asset set changed on this page")
        if collections.Counter(snapshot_canonical["links"]) != collections.Counter(refined_canonical["links"]):
            page_errors.append("link destinations changed on this page")
        if snapshot_callouts != refined_callouts:
            page_errors.append("Callout headers changed, were added/removed, or were reordered")
        if snapshot_conversion != refined_conversion:
            page_errors.append("conversion-layer provenance markers changed, were added/removed, or were reordered")
        if page_id is None:
            if snapshot_page != refined_page:
                page_errors.append("document preamble changed")
        else:
            without_comments = re.sub(r"<!--.*?-->", "", text_without_math(refined_page), flags=re.S)
            if re.search(r"</?[A-Za-z][^>]*>", without_comments):
                page_errors.append("raw HTML is forbidden; use native Markdown or math delimiters")
        if page_errors:
            errors.extend(f"page {page_id if page_id is not None else 'preamble'}: {item}" for item in page_errors)
        page_results.append(
            {
                "page": page_id,
                "changed": snapshot_page != refined_page,
                "snapshot_math_spans": len(snapshot_canonical["math"]),
                "refined_math_spans": len(refined_canonical["math"]),
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
        "pages": page_results,
        "errors": errors,
    }


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def restore_in_place(path: Path, content: bytes) -> None:
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
    parser.add_argument("--target", required=True, type=Path, help="Normalized Markdown note inside the vault")
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
    except HANDLED_ERRORS as exc:
        restored = False
        restore_error = None
        if snapshot_bytes is not None:
            if target_path.is_file():
                try:
                    restore_in_place(target_path, snapshot_bytes)
                    restored = True
                except OSError as rollback_exc:
                    restore_error = str(rollback_exc)
        print(json.dumps({"valid": False, "error": str(exc), "restored": restored, "restore_error": restore_error}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
