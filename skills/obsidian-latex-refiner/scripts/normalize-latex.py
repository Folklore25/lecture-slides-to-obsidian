#!/usr/bin/env python3
"""Analyze and normalize LaTeX math in an Obsidian note so equations render in MathJax."""

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

TRANSFORM_GROUPS = ("shell", "delimiters", "environments", "labels", "cjk", "multiline-inline")

EQUATION_UNWRAP = {"equation", "equation*"}
DISPLAY_DELIMITER_ENVS = {"displaymath"}
ALIGN_OUTPUT = {"align", "align*", "eqnarray", "eqnarray*", "flalign", "flalign*", "alignat", "alignat*", "split", "aligned"}
GATHER_OUTPUT = {"gather", "gather*", "multline", "multline*", "gathered"}
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
TEXT_COMMAND_PREFIX = re.compile(r"\\(?:text|mbox|textrm|textnormal)\s*\{[^{}]*$")
DOC_PATTERNS = (
    (re.compile(r"\\begin\{table\}|\\begin\{tabular\}"), "document_latex_table", "document-level LaTeX table; keep the extracted image or convert it manually"),
    (re.compile(r"\\includegraphics"), "document_latex_image", "LaTeX image command; replace it with an Obsidian embed of the extracted asset"),
    (re.compile(r"\\href|\\url"), "document_latex_link", "LaTeX link command; convert it to a Markdown link"),
    (re.compile(r"\\cite|\\ref|\\eqref|\\footnote"), "document_latex_reference", "LaTeX reference or footnote command that MathJax will not render"),
)
STAT_KEYS = (
    "math_spans",
    "inline_math_spans",
    "display_math_spans",
    "redundant_display_shells_collapsed",
    "inline_parenthesis_delimiters",
    "inline_math_envs",
    "display_bracket_delimiters",
    "display_math_envs",
    "unwrapped_equation_envs",
    "unwrapped_inner_equation_envs",
    "renamed_environments",
    "wrapped_matrix_envs",
    "stripped_labels",
    "stripped_numbering_commands",
    "cjk_runs_wrapped",
    "promoted_multiline_inline",
    "empty_math_skipped",
)


def load_validator():
    spec = importlib.util.spec_from_file_location("lecture_latex_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load validate-latex-refinement.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V = load_validator()


def empty_stats() -> dict:
    return {key: 0 for key in STAT_KEYS}


def parse_only(value: str | None, no_cjk: bool) -> set:
    groups = set(TRANSFORM_GROUPS)
    if value is not None:
        requested = {part.strip() for part in value.split(",") if part.strip()}
        unknown = sorted(requested - set(TRANSFORM_GROUPS))
        if unknown:
            raise V.RefinementError("unknown --only transform group(s): " + ", ".join(unknown))
        groups = requested
    if no_cjk:
        groups.discard("cjk")
    return groups


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


def has_raw_cjk(text: str) -> bool:
    index = 0
    length = len(text)
    while index < length:
        if V.CJK.match(text[index]):
            end = index
            while end < length and V.CJK.match(text[end]):
                end += 1
            if not TEXT_COMMAND_PREFIX.search(text[:index]):
                return True
            index = end
        else:
            index += 1
    return False


def clean_math_inner(inner: str, stats: dict, enabled: set) -> str:
    value = inner
    if "labels" in enabled:
        value, count = V.LABEL.subn("", value)
        stats["stripped_labels"] += count
        value, count = V.NONUMBER.subn("", value)
        stats["stripped_numbering_commands"] += count
    if "environments" in enabled:
        for env in sorted(EQUATION_UNWRAP):
            pattern = re.compile(r"\\begin\{" + re.escape(env) + r"\}(.*?)\\end\{" + re.escape(env) + r"\}", re.S)
            value, count = pattern.subn(r"\1", value)
            stats["unwrapped_inner_equation_envs"] += count

        def begin(match: re.Match) -> str:
            name = match.group(1) or ""
            renamed = ENV_RENAME.get(name, name)
            if renamed != name:
                stats["renamed_environments"] += 1
            return "\\begin{" + renamed + "}"

        def end(match: re.Match) -> str:
            name = match.group(1) or ""
            return "\\end{" + ENV_RENAME.get(name, name) + "}"

        value = re.sub(r"\\begin\{([A-Za-z*]+)\}", begin, value)
        value = re.sub(r"\\end\{([A-Za-z*]+)\}", end, value)
    if "cjk" in enabled:
        value = wrap_cjk_runs(value, stats)
    return value


def render_span(span: dict, stats: dict, enabled: set) -> str:
    env = span["env"]
    raw = span["raw"]
    body = clean_math_inner(span["inner"], stats, enabled).strip()
    if span["kind"] == "inline":
        stats["inline_math_spans"] += 1
        if not body:
            stats["empty_math_skipped"] += 1
            return raw
        if env == "math":
            if "delimiters" not in enabled:
                return raw
            stats["inline_math_envs"] += 1
            return "$" + body + "$"
        if raw.startswith("\\("):
            if "delimiters" not in enabled:
                return raw
            stats["inline_parenthesis_delimiters"] += 1
        if "\n" in span["inner"]:
            if "multiline-inline" not in enabled:
                return raw
            stats["promoted_multiline_inline"] += 1
            return "$$\n" + body + "\n$$"
        return "$" + body + "$"
    stats["display_math_spans"] += 1
    if not body:
        stats["empty_math_skipped"] += 1
        return raw
    if env in EQUATION_UNWRAP:
        if "environments" not in enabled:
            return raw
        stats["unwrapped_equation_envs"] += 1
        return "$$\n" + body + "\n$$"
    if env in DISPLAY_DELIMITER_ENVS:
        if "delimiters" not in enabled:
            return raw
        stats["display_math_envs"] += 1
        return "$$\n" + body + "\n$$"
    if env in ALIGN_OUTPUT:
        if "environments" not in enabled:
            return raw
        return "$$\n\\begin{aligned}\n" + body + "\n\\end{aligned}\n$$"
    if env in GATHER_OUTPUT:
        if "environments" not in enabled:
            return raw
        return "$$\n\\begin{gathered}\n" + body + "\n\\end{gathered}\n$$"
    if env in V.MATRIX_ENVS:
        if "environments" not in enabled:
            return raw
        stats["wrapped_matrix_envs"] += 1
        return "$$\n\\begin{" + env + "}" + body + "\\end{" + env + "}\n$$"
    if raw.startswith("\\["):
        if "delimiters" not in enabled:
            return raw
        stats["display_bracket_delimiters"] += 1
    return "$$\n" + body + "\n$$"


def normalize_text(text: str, enabled: set) -> tuple[str, dict]:
    stats = empty_stats()
    masked, blocks = V.mask_verbatim(text)
    if "shell" in enabled:
        working, shell_count = V.collapse_redundant_display(masked)
        stats["redundant_display_shells_collapsed"] = shell_count
    else:
        working = masked
    spans = V.find_math_spans(working)
    stats["math_spans"] = len(spans)
    parts: list[str] = []
    cursor = 0
    for span in spans:
        parts.append(working[cursor:span["start"]])
        parts.append(render_span(span, stats, enabled))
        cursor = span["end"]
    parts.append(working[cursor:])
    return V.unmask_verbatim("".join(parts), blocks), stats


def dollar_balance(text: str) -> int:
    index = 0
    length = len(text)
    count = 0
    while index < length:
        if text[index] == "\\" and index + 1 < length and text[index + 1] == "$":
            index += 2
            continue
        if text[index] == "$":
            count += 1
        index += 1
    return count


def analyze_page(page_text: str) -> dict:
    masked, _ = V.mask_verbatim(page_text)
    collapsed, shell_count = V.collapse_redundant_display(masked)
    spans = V.find_math_spans(collapsed)
    issues: dict = {}

    def bump(kind: str, amount: int = 1) -> None:
        issues[kind] = issues.get(kind, 0) + amount

    if shell_count:
        bump("redundant_display_shell", shell_count)
    environments: dict = {}
    inline = 0
    display = 0
    for span in spans:
        if span["kind"] == "inline":
            inline += 1
        else:
            display += 1
        env = span["env"]
        if env:
            environments[env] = environments.get(env, 0) + 1
        raw = span["raw"]
        if raw.startswith("\\(") or env == "math":
            bump("legacy_inline_delimiter")
        if raw.startswith("\\["):
            bump("legacy_display_delimiter")
        if span["kind"] == "display" and span["inner"].strip() == "":
            bump("empty_display_math")
        if span["kind"] == "inline" and "\n" in span["inner"]:
            bump("multiline_inline_math")
        if V.LABEL.search(span["inner"]):
            bump("label_command")
        if V.NONUMBER.search(span["inner"]):
            bump("numbering_command")
        if has_raw_cjk(span["inner"]):
            bump("raw_cjk_in_math")
    if dollar_balance(masked) % 2:
        bump("unbalanced_dollar")
    if masked.count("\\(") != masked.count("\\)"):
        bump("unbalanced_parenthesis_delimiter")
    if masked.count("\\[") != masked.count("\\]"):
        bump("unbalanced_bracket_delimiter")
    for pattern, kind, _ in DOC_PATTERNS:
        found = len(pattern.findall(masked))
        if found:
            bump(kind, found)
    return {
        "math_spans": len(spans),
        "inline": inline,
        "display": display,
        "environments": environments,
        "issues": issues,
    }


def analyze_text(text: str, target: str) -> dict:
    try:
        _, body = V.split_frontmatter(text)
    except V.RefinementError:
        body = text
    _, segments, page_ids = V.split_pages(body)
    pages = []
    totals: dict = {}
    environment_totals: dict = {}
    for index, segment in enumerate(segments):
        page = analyze_page(segment)
        page["page"] = page_ids[index]
        pages.append(page)
        for key, value in page["issues"].items():
            totals[key] = totals.get(key, 0) + value
        for key, value in page["environments"].items():
            environment_totals[key] = environment_totals.get(key, 0) + value
    recommended = set()
    if {"redundant_display_shell", "empty_display_math"} & set(totals):
        recommended.add("shell")
    if {"legacy_inline_delimiter", "legacy_display_delimiter"} & set(totals):
        recommended.add("delimiters")
    if environment_totals:
        recommended.add("environments")
    if {"label_command", "numbering_command"} & set(totals):
        recommended.add("labels")
    if "raw_cjk_in_math" in totals:
        recommended.add("cjk")
    if "multiline_inline_math" in totals:
        recommended.add("multiline-inline")
    review = [message for _, kind, message in DOC_PATTERNS if totals.get(kind)]
    if totals.get("unbalanced_dollar") or totals.get("unbalanced_parenthesis_delimiter") or totals.get("unbalanced_bracket_delimiter"):
        review.append("an unbalanced math delimiter was detected; inspect the affected page before normalizing")
    return {
        "schema_version": 1,
        "mode": "analyze",
        "target": target,
        "page_markers": [page for page in page_ids[1:] if page is not None],
        "pages": pages,
        "totals": totals,
        "environments": environment_totals,
        "recommended_transforms": sorted(recommended),
        "review_items": review,
    }


def resolve_vault_root(target: Path, explicit: Path | None) -> tuple[Path, str]:
    if explicit is not None:
        return explicit.resolve(), "explicit"
    for parent in target.parents:
        if (parent / ".obsidian").is_dir():
            return parent, "detected"
    return target.parent, "target-directory"


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path, help="Markdown note to analyze or normalize")
    parser.add_argument("--vault-root", type=Path, help="Vault root; auto-detected from a .obsidian ancestor when omitted")
    parser.add_argument("--snapshot", type=Path, help="Byte-exact pre-edit snapshot outside the vault (fix mode)")
    parser.add_argument("--report", type=Path, help="Temporary JSON report outside the vault")
    parser.add_argument("--analyze", action="store_true", help="Read-only pre-scan; print issues and recommended transforms")
    parser.add_argument("--dry-run", action="store_true", help="Write the proposed text next to the snapshot without touching the target")
    parser.add_argument("--dry-run-output", type=Path, help="Explicit path for the proposed text")
    parser.add_argument("--allow-lecture-layers", action="store_true", help="Allow a math-only pass on a note that already has lecture-layer blocks")
    parser.add_argument("--only", help="Comma-separated transform groups: " + ", ".join(TRANSFORM_GROUPS))
    parser.add_argument("--no-cjk", action="store_true", help="Do not wrap raw CJK runs inside math")
    parser.add_argument("--report-format", choices=("json", "text"), default="json")
    args = parser.parse_args()
    target_path = args.target.resolve()
    report_format = args.report_format
    try:
        if not target_path.is_file():
            raise V.RefinementError("target Markdown does not exist")
        if args.analyze:
            analysis = analyze_text(target_path.read_text(encoding="utf-8"), str(target_path))
            summary = summarize_analysis(analysis)
            if args.report is not None:
                V.write_json_atomic(args.report.resolve(), {**analysis, "summary": summary})
            if report_format == "text":
                print("\n".join(summary))
            else:
                print(json.dumps({**analysis, "summary": summary}, ensure_ascii=False, indent=2))
            return 0
        enabled = parse_only(args.only, args.no_cjk)
        if args.snapshot is None or args.report is None:
            raise V.RefinementError("fix mode requires --snapshot and --report; use --analyze for a read-only scan")
        vault_root, vault_source = resolve_vault_root(target_path, args.vault_root)
        snapshot_path = args.snapshot.resolve()
        report_path = args.report.resolve()
        if args.snapshot.is_symlink() or args.target.is_symlink() or args.report.is_symlink():
            raise V.RefinementError("target, snapshot, and report must not be symlinks")
        if not V.inside(target_path, vault_root):
            raise V.RefinementError("target Markdown must be inside the vault root")
        relative_target = target_path.relative_to(vault_root)
        if any(part.startswith(".") for part in relative_target.parts):
            raise V.RefinementError("target Markdown must not be inside a dot-prefixed vault path")
        if V.inside(snapshot_path, vault_root) or V.inside(report_path, vault_root):
            raise V.RefinementError("snapshot and report must be outside the Obsidian vault")
        if snapshot_path == target_path or report_path in (snapshot_path, target_path):
            raise V.RefinementError("snapshot, target, and report paths must be distinct")
        original_bytes = target_path.read_bytes()
        original = original_bytes.decode("utf-8")
        normalized, stats = normalize_text(original, enabled)
        result = V.validate_refinement(original, normalized, allow_lecture_layers=args.allow_lecture_layers)
        result["mode"] = "dry-run" if args.dry_run else "fix"
        result["snapshot"] = str(snapshot_path)
        result["target"] = str(target_path)
        result["report"] = str(report_path)
        result["vault_root"] = str(vault_root)
        result["vault_root_source"] = vault_source
        result["enabled_transforms"] = sorted(enabled)
        result["transform_counts"] = stats
        result["review_items"] = review_items_for(original, normalized)
        result["restored"] = False
        if args.dry_run:
            proposed_path = args.dry_run_output.resolve() if args.dry_run_output else snapshot_path.with_name(snapshot_path.stem + ".refined.md")
            write_text_atomic(proposed_path, normalized)
            result["proposed_path"] = str(proposed_path)
            result["would_be_valid"] = result["valid"]
        else:
            write_bytes_atomic(snapshot_path, original_bytes)
            if result["valid"]:
                if normalized != original:
                    write_text_atomic(target_path, normalized)
            else:
                V.restore_in_place(target_path, original_bytes)
                result["restored"] = True
                result["restored_sha256"] = hashlib.sha256(target_path.read_bytes()).hexdigest()
        result["summary"] = V.summarize(result)
        V.write_json_atomic(report_path, result)
        V.print_report(result, report_format)
        return 0 if result["valid"] else 1
    except V.HANDLED_ERRORS as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


def summarize_analysis(analysis: dict) -> list[str]:
    lines = ["mode: analyze", "target: " + analysis.get("target", "")]
    lines.append(f"math spans: {sum(page['math_spans'] for page in analysis['pages'])}")
    totals = analysis.get("totals") or {}
    if totals:
        lines.append("issues: " + ", ".join(f"{key}={value}" for key, value in sorted(totals.items())))
    else:
        lines.append("issues: none")
    recommended = analysis.get("recommended_transforms") or []
    lines.append("recommended transforms: " + (", ".join(recommended) if recommended else "none"))
    for item in analysis.get("review_items") or []:
        lines.append("review: " + item)
    for page in analysis["pages"]:
        if page["issues"]:
            lines.append(f"page {page['page']}: " + ", ".join(f"{key}={value}" for key, value in sorted(page["issues"].items())))
    return lines


def review_items_for(original: str, normalized: str) -> list[str]:
    items: list[str] = []
    for pattern, _, message in DOC_PATTERNS:
        if pattern.search(normalized):
            items.append(message)
    masked, _ = V.mask_verbatim(normalized)
    if dollar_balance(masked) % 2:
        items.append("an unbalanced dollar delimiter remains; verify the affected page manually")
    if masked.count("\\(") != masked.count("\\)"):
        items.append("an unbalanced parenthesis math delimiter remains; verify the affected page manually")
    if masked.count("\\[") != masked.count("\\]"):
        items.append("an unbalanced bracket math delimiter remains; verify the affected page manually")
    return items


if __name__ == "__main__":
    sys.exit(main())
