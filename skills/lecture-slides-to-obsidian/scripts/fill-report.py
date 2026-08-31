#!/usr/bin/env python3
"""Render the temporary QA conversion report from validated JSON context."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path


REQUIRED_TOP_LEVEL = {
    "routing", "pipeline", "outputs", "inventory", "quality_gates",
    "review_items", "not_checked",
}
INVENTORY_KEYS = {
    "pages", "figures_images", "tables", "equations", "fallback_pages",
    "page_headers", "page_footers", "page_footnotes",
}
FORBIDDEN_KEY_PARTS = {"token", "passphrase", "authorization", "signed_url", "source_path"}
SECRET_PATTERNS = [
    re.compile(r"Authorization:\s*Bearer", re.I),
    re.compile(r"https?://\S+\?\S+"),
    re.compile(r"/Users/[^\s|]+"),
    re.compile(r"/home/[^\s|]+"),
]


class ReportError(RuntimeError):
    pass


def _flatten(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path, item
            yield from _flatten(item, path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _flatten(item, f"{prefix}[{index}]")


def validate_context(context: dict) -> None:
    missing = REQUIRED_TOP_LEVEL - context.keys()
    if missing:
        raise ReportError("missing context sections: " + ", ".join(sorted(missing)))
    missing_inventory = INVENTORY_KEYS - context["inventory"].keys()
    if missing_inventory:
        raise ReportError("missing inventory fields: " + ", ".join(sorted(missing_inventory)))
    for key in INVENTORY_KEYS:
        value = context["inventory"][key]
        if not isinstance(value, int) or value < 0:
            raise ReportError(f"inventory.{key} must be a non-negative integer")
    for path, value in _flatten(context):
        normalized = path.lower().replace("-", "_")
        if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
            raise ReportError(f"forbidden secret/path field: {path}")
        if isinstance(value, str) and any(pattern.search(value) for pattern in SECRET_PATTERNS):
            raise ReportError(f"secret URL/header or absolute path in field: {path}")
    if not isinstance(context["review_items"], list) or not isinstance(context["not_checked"], list):
        raise ReportError("review_items and not_checked must be arrays")


def _table(mapping: dict) -> list[str]:
    lines = ["| Field | Value |", "| --- | --- |"]
    for key, value in mapping.items():
        label = str(key).replace("_", " ").strip().title()
        rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
        escaped = rendered.replace("|", "\\|")
        lines.append(f"| {label} | {escaped} |")
    return lines


def render_report(context: dict) -> str:
    validate_context(context)
    inventory = context["inventory"]
    labels = [
        ("Pages", "pages"),
        ("Figures/images", "figures_images"),
        ("Tables", "tables"),
        ("Equations", "equations"),
        ("Fallback pages", "fallback_pages"),
        ("Page headers", "page_headers"),
        ("Page footers", "page_footers"),
        ("Page footnotes", "page_footnotes"),
    ]
    lines = ["# Conversion report", "", "## Matched routing", ""]
    lines += _table(context["routing"])
    lines += ["", "## Pipeline", ""] + _table(context["pipeline"])
    lines += ["", "## Outputs", ""] + _table(context["outputs"])
    lines += ["", "## Content inventory", "", "| Type | Count |", "| --- | ---: |"]
    lines += [f"| {label} | {inventory[key]} |" for label, key in labels]
    lines += ["", "## Quality gates", ""] + _table(context["quality_gates"])
    lines += ["", "## Review items", ""]
    if context["review_items"]:
        for item in context["review_items"]:
            lines += ["> [!warning] REVIEW", f"> {item}", ""]
    else:
        lines += ["- None.", ""]
    lines += ["## Not checked", ""]
    if context["not_checked"]:
        lines += [f"- {item}" for item in context["not_checked"]]
    else:
        lines.append("- None.")
    return "\n".join(lines).rstrip() + "\n"


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
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        context = json.loads(args.context.read_text(encoding="utf-8"))
        write_atomic(args.output, render_report(context))
    except (OSError, json.JSONDecodeError, ReportError) as exc:
        print(f"fill-report error: {exc}", file=sys.stderr)
        return 1
    print(f"temporary conversion report written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
