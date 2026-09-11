#!/usr/bin/env python3
"""Normalize MinerU LaTeX into Obsidian-renderable math in place with conservation rollback."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR_PATH = SCRIPT_DIR / "validate-latex-refinement.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("lecture_latex_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load validate-latex-refinement.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V = load_validator()

ENV_RENAME = {
    "align": "aligned",
    "align*": "aligned",
    "eqnarray": "aligned",
    "eqnarray*": "aligned",
    "flalign": "aligned",
    "flalign*": "aligned",
    "alignat": "aligned",
    "alignat*": "aligned",
    "split": "aligned",
    "gather": "gathered",
    "gather*": "gathered",
    "multline": "gathered",
    "multline*": "gathered",
}
ALIGN_OUTPUT = {"align", "align*", "eqnarray", "eqnarray*", "flalign", "flalign*", "alignat", "alignat*", "split", "aligned"}
GATHER_OUTPUT = {"gather", "gather*", "multline", "multline*", "gathered"}
EQUATION_OUTPUT = {"equation", "equation*", "displaymath"}
TEXT_COMMAND_PREFIX = re.compile(r"\\(?:text|mbox|textrm|textnormal)\s*\{[^{}]*$")
REVIEW_PATTERNS = (
    (re.compile(r"\\begin\{table\}|\\begin\{tabular\}"), "document-level LaTeX table remains; keep the extracted table image or convert it manually"),
    (re.compile(r"\\includegraphics"), "LaTeX image command remains; replace it with an Obsidian embed of the extracted asset"),
    (re.compile(r"\\href|\\url"), "LaTeX link command remains; convert it to a Markdown link"),
    (re.compile(r"\\cite|\\ref|\\eqref|\\footnote"), "LaTeX reference or footnote command remains and will not render"),
)
STAT_KEYS = (
    "math_spans",
    "inline_math_spans",
    "display_math_spans",
    "unwrapped_equation_envs",
    "unwrapped_inner_equation_envs",
    "aligned_envs",
    "gathered_envs",
    "wrapped_matrix_envs",
    "stripped_labels",
    "stripped_numbering_commands",
    "cjk_runs_wrapped",
    "promoted_multiline_inline",
    "empty_math_skipped",
)


def empty_stats() -> dict:
    return {key: 0 for key in STAT_KEYS}


def clean_math_inner(inner: str, stats: dict, wrap_cjk: bool) -> str:
    value, count = V.LABEL.subn("", inner)
    stats["stripped_labels"] += count
    value, count = V.NONUMBER.subn("", value)
    stats["stripped_numbering_commands"] += count
    for env in sorted(EQUATION_OUTPUT):
        pattern = re.compile(r"\\begin\{" + re.escape(env) + r"\}(.*?)\\end\{" + re.escape(env) + r"\}", re.S)
        value, count = pattern.subn(r"\1", value)
        stats["unwrapped_inner_equation_envs"] += count
    value, count = re.subn(
        r"\\begin\{([A-Za-z*]+)\}",
        lambda match: "\\begin{" + ENV_RENAME.get(match.group(1), match.group(1)) + "}",
        value,
    )
    stats["aligned_envs"] += sum(1 for name in re.findall(r"\\begin\{([A-Za-z*]+)\}", value) if ENV_RENAME.get(name) == "aligned")
    value, _ = re.subn(
        r"\\end\{([A-Za-z*]+)\}",
        lambda match: "\\end{" + ENV_RENAME.get(match.group(1), match.group(1)) + "}",
        value,
    )
    if wrap_cjk:
        value = wrap_cjk_runs(value, stats)
    return value


def wrap_cjk_runs(text: str, stats: dict) -> str:
    result: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        if V.CJK.match(text[index]):
            end = index
            while end < length and V.CJK.match(text[end]):
                end += 1
            run = text[index:end]
            if TEXT_COMMAND_PREFIX.search(text[:index]):
                result.append(run)
            else:
                result.append("\\text{" + run + "}")
                stats["cjk_runs_wrapped"] += 1
            index = end
        else:
            result.append(text[index])
            index += 1
    return "".join(result)


def render_span(span: dict, stats: dict, wrap_cjk: bool) -> str:
    inner = clean_math_inner(span["inner"], stats, wrap_cjk)
    body = inner.strip()
    env = span["env"]
    if span["kind"] == "inline":
        stats["inline_math_spans"] += 1
        if not body:
            stats["empty_math_skipped"] += 1
            return span["inner"]
        if "\n" in inner:
            stats["promoted_multiline_inline"] += 1
            return "$$\n" + body + "\n$$"
        return "$" + body + "$"
    stats["display_math_spans"] += 1
    if not body:
        stats["empty_math_skipped"] += 1
        return span["inner"]
    if env in EQUATION_OUTPUT:
        stats["unwrapped_equation_envs"] += 1
        return "$$\n" + body + "\n$$"
    if env in ALIGN_OUTPUT:
        return "$$\n\\begin{aligned}\n" + body + "\n\\end{aligned}\n$$"
    if env in GATHER_OUTPUT:
        return "$$\n\\begin{gathered}\n" + body + "\n\\end{gathered}\n$$"
    if env in V.MATRIX_ENVS:
        stats["wrapped_matrix_envs"] += 1
        return "$$\n\\begin{" + env + "}" + body + "\\end{" + env + "}\n$$"
    return "$$\n" + body + "\n$$"


def normalize_text(text: str, wrap_cjk: bool = True) -> tuple[str, dict]:
    stats = empty_stats()
    masked, blocks = V.mask_verbatim(text)
    spans = V.find_math_spans(masked)
    stats["math_spans"] = len(spans)
    parts: list[str] = []
    cursor = 0
    for span in spans:
        parts.append(masked[cursor:span["start"]])
        parts.append(render_span(span, stats, wrap_cjk))
        cursor = span["end"]
    parts.append(masked[cursor:])
    normalized = V.unmask_verbatim("".join(parts), blocks)
    return normalized, stats


def dollar_balance(text: str) -> int:
    masked, _ = V.mask_verbatim(text)
    index = 0
    length = len(masked)
    count = 0
    while index < length:
        if masked[index] == "\\" and index + 1 < length and masked[index + 1] == "$":
            index += 2
            continue
        if masked[index] == "$":
            count += 1
        index += 1
    return count


def review_items(normalized: str) -> list[str]:
    items: list[str] = []
    for pattern, message in REVIEW_PATTERNS:
        if pattern.search(normalized):
            items.append(message)
    if dollar_balance(normalized) % 2:
        items.append("an unbalanced dollar delimiter remains; verify the affected page manually")
    return items


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
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
    parser.add_argument("--target", required=True, type=Path, help="Final Markdown note inside the vault")
    parser.add_argument("--vault-root", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path, help="Byte-exact pre-edit snapshot outside the vault")
    parser.add_argument("--report", required=True, type=Path, help="Temporary normalization report outside the vault")
    parser.add_argument("--no-cjk", action="store_true", help="Do not wrap raw CJK runs inside math in a text command")
    args = parser.parse_args()
    target_path = args.target.resolve()
    vault_root = args.vault_root.resolve()
    snapshot_path = args.snapshot.resolve()
    report_path = args.report.resolve()
    snapshot_bytes = None
    try:
        if args.target.is_symlink() or args.snapshot.is_symlink() or args.report.is_symlink():
            raise V.RefinementError("target, snapshot, and report must not be symlinks")
        if not V.inside(target_path, vault_root):
            raise V.RefinementError("target Markdown must be inside --vault-root")
        relative_target = target_path.relative_to(vault_root)
        if any(part.startswith(".") for part in relative_target.parts):
            raise V.RefinementError("target Markdown must not be inside a dot-prefixed vault path")
        if V.inside(snapshot_path, vault_root) or V.inside(report_path, vault_root):
            raise V.RefinementError("snapshot and report must be outside the Obsidian vault")
        if snapshot_path == target_path or report_path in (snapshot_path, target_path):
            raise V.RefinementError("snapshot, target, and report paths must be distinct")
        snapshot_bytes = target_path.read_bytes()
        original = snapshot_bytes.decode("utf-8")
        write_bytes_atomic(snapshot_path, snapshot_bytes)
        normalized, stats = normalize_text(original, wrap_cjk=not args.no_cjk)
        result = V.validate_refinement(original, normalized)
        result["schema_version"] = 1
        result["snapshot"] = str(snapshot_path)
        result["target"] = str(target_path)
        result["report"] = str(report_path)
        result["cjk_wrapping"] = not args.no_cjk
        result["transform_counts"] = stats
        result["review_items"] = review_items(normalized)
        result["restored"] = False
        if result["valid"]:
            if normalized != original:
                write_text_atomic(target_path, normalized)
        else:
            V.restore_in_place(target_path, snapshot_bytes)
            result["restored"] = True
            result["restored_sha256"] = hashlib.sha256(target_path.read_bytes()).hexdigest()
        V.write_json_atomic(report_path, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    except V.HANDLED_ERRORS as exc:
        restored = False
        restore_error = None
        if snapshot_bytes is not None:
            if target_path.is_file():
                try:
                    V.restore_in_place(target_path, snapshot_bytes)
                    restored = True
                except OSError as rollback_exc:
                    restore_error = str(rollback_exc)
        print(json.dumps({"valid": False, "error": str(exc), "restored": restored, "restore_error": restore_error}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
