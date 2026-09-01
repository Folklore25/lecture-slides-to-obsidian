#!/usr/bin/env python3
"""Apply idempotent student/teacher callout patches to an Obsidian course note."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ENTRY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,80}$")
STUDENT_KINDS = {
    "thought", "connection", "question", "interpretation", "example",
    "disagreement", "hypothesis", "action",
}
TEACHER_KINDS = {
    "explanation", "example", "emphasis", "correction", "boundary",
    "question-answer", "logistics",
}
CALLOUTS = {
    ("student", "question"): ("question", "In-class question"),
    ("student", "example"): ("example", "In-class example"),
    ("student", "action"): ("todo", "In-class action"),
    ("student", "connection"): ("note", "In-class connection"),
    ("teacher", "example"): ("example", "Lecturer example"),
    ("teacher", "emphasis"): ("important", "Lecturer emphasis"),
    ("teacher", "correction"): ("warning", "Lecturer correction"),
    ("teacher", "boundary"): ("warning", "Lecturer boundary"),
    ("teacher", "question-answer"): ("question", "Lecturer Q&A"),
    ("teacher", "logistics"): ("info", "Course logistics"),
}


class PatchError(RuntimeError):
    pass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_note_path(value: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or path.suffix.lower() != ".md":
        raise PatchError("note must be a vault-relative Markdown path without '..'")
    return path.as_posix()


def validate_patch(patch: dict) -> tuple[str, list[dict]]:
    if not isinstance(patch, dict) or patch.get("schema_version") != 1:
        raise PatchError("patch must be an object with schema_version 1")
    note = validate_note_path(patch.get("note", ""))
    entries = patch.get("entries")
    if not isinstance(entries, list) or not entries:
        raise PatchError("entries must contain at least one patch entry")
    seen = set()
    normalized = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise PatchError(f"entries[{index}] must be an object")
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not ENTRY_ID.fullmatch(entry_id) or entry_id in seen:
            raise PatchError(f"entries[{index}].id must be unique and URL-safe")
        seen.add(entry_id)
        actor = entry.get("actor")
        kind = entry.get("kind")
        allowed = STUDENT_KINDS if actor == "student" else TEACHER_KINDS if actor == "teacher" else set()
        if kind not in allowed:
            raise PatchError(f"entries[{index}] actor/kind combination is unsupported: {actor!r}/{kind!r}")
        heading = entry.get("target_heading")
        level = entry.get("target_level")
        body = entry.get("body")
        if not isinstance(heading, str) or not heading.strip() or level not in {2, 3}:
            raise PatchError(f"entries[{index}] needs an exact H2/H3 target_heading and target_level")
        if not isinstance(body, str) or not body.strip() or len(body.strip()) > 2000:
            raise PatchError(f"entries[{index}].body must contain 1..2000 characters")
        if "<!-- lecture-layer:" in body:
            raise PatchError(f"entries[{index}].body contains reserved marker syntax")
        routing_status = entry.get("routing_status", "matched")
        if routing_status not in {"matched", "unresolved"}:
            raise PatchError(f"entries[{index}].routing_status must be matched or unresolved")
        if routing_status == "unresolved" and not (heading == "In-class notes" and level == 2):
            raise PatchError("unresolved entries must target the exact H2 'In-class notes'")
        normalized.append({**entry, "target_heading": heading.strip(), "body": body.strip()})
    return note, normalized


def markdown_headings(text: str) -> list[dict]:
    headings = []
    fenced = False
    fence_token = None
    offset = 0
    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        stripped = line.lstrip()
        fence = re.match(r"^(```+|~~~+)", stripped)
        if fence:
            token = fence.group(1)[0]
            if not fenced:
                fenced, fence_token = True, token
            elif token == fence_token:
                fenced, fence_token = False, None
            offset += len(line)
            continue
        if not fenced:
            match = re.match(r"^(#{1,6})\s+(.+?)\s*(?:\n)?$", line)
            if match:
                headings.append(
                    {
                        "level": len(match.group(1)),
                        "title": match.group(2).strip(),
                        "line": line_number,
                        "start": offset,
                    }
                )
        offset += len(line)
    return headings


def frontmatter_type(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    for line in text[4:end].splitlines():
        match = re.match(r"^type:\s*(.*?)\s*$", line)
        if match:
            return match.group(1).strip("\"'")
    return None


def render_block(entry: dict) -> str:
    actor, kind, entry_id = entry["actor"], entry["kind"], entry["id"]
    callout, title = CALLOUTS.get(
        (actor, kind),
        ("note", "In-class thought") if actor == "student" else ("info", "Lecturer explanation"),
    )
    body_lines = [f"> {line}" if line else ">" for line in entry["body"].splitlines()]
    metadata = []
    if entry.get("captured_at"):
        metadata.append(f"Captured: {entry['captured_at']}")
    if entry.get("source_anchor"):
        metadata.append(f"ASR: {entry['source_anchor']}")
    if entry.get("confidence"):
        metadata.append(f"Confidence: {entry['confidence']}")
    if entry.get("routing_status") == "unresolved":
        metadata.append("Routing: unresolved")
    lines = [
        f"<!-- lecture-layer:{actor}:{entry_id}:start -->",
        f"> [!{callout}] {title}",
        *body_lines,
    ]
    if metadata:
        lines += [">", f"> _{' · '.join(metadata)}_"]
    lines.append(f"<!-- lecture-layer:{actor}:{entry_id}:end -->")
    return "\n".join(lines)


def apply_entries(text: str, entries: list[dict]) -> tuple[str, list[dict]]:
    result = text
    outcomes = []
    for entry in entries:
        marker = f"<!-- lecture-layer:{entry['actor']}:{entry['id']}:start -->"
        if marker in result:
            outcomes.append({"id": entry["id"], "status": "already_present"})
            continue
        headings = markdown_headings(result)
        matches = [
            heading for heading in headings
            if heading["level"] == entry["target_level"] and heading["title"] == entry["target_heading"]
        ]
        if len(matches) != 1:
            available = [
                f"H{heading['level']} {heading['title']}"
                for heading in headings if heading["level"] in {2, 3}
            ][:12]
            raise PatchError(
                f"entry {entry['id']} target is {'missing' if not matches else 'ambiguous'}: "
                f"H{entry['target_level']} {entry['target_heading']!r}; available={available}"
            )
        target = matches[0]
        later = [
            heading for heading in headings
            if heading["start"] > target["start"] and heading["level"] <= target["level"]
        ]
        insert_at = later[0]["start"] if later else len(result)
        prefix, suffix = result[:insert_at], result[insert_at:]
        leading = "\n" if prefix.endswith("\n") else "\n\n"
        trailing = "\n" if suffix.startswith("\n") or not suffix else "\n\n"
        result = prefix + leading + render_block(entry) + trailing + suffix
        outcomes.append(
            {
                "id": entry["id"],
                "status": "inserted",
                "target_heading": entry["target_heading"],
                "target_level": entry["target_level"],
            }
        )
    return result, outcomes


def run_cli(arguments: list[str], vault_root: Path) -> str:
    completed = subprocess.run(arguments, cwd=vault_root, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise PatchError((completed.stderr or completed.stdout).strip() or "Obsidian CLI command failed")
    return completed.stdout


def obsidian_read(note: str, vault_root: Path) -> str:
    return run_cli(["obsidian", "read", f"path={note}"], vault_root)


def write_atomic(path: Path, content: str) -> None:
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


def write_note(note: str, original: str, modified: str, vault_root: Path) -> str:
    latest = obsidian_read(note, vault_root)
    if sha256_text(latest) != sha256_text(original):
        raise PatchError("note changed after planning; re-read and rebuild the patch before writing")
    arg_limit = os.sysconf("SC_ARG_MAX") if hasattr(os, "sysconf") else 262144
    encoded_size = len(modified.encode("utf-8"))
    if encoded_size < min(180000, arg_limit // 2):
        run_cli(["obsidian", "create", f"path={note}", f"content={modified}", "overwrite"], vault_root)
        writer = "obsidian-cli-create"
    else:
        destination = (vault_root / note).resolve()
        try:
            destination.relative_to(vault_root.resolve())
        except ValueError as exc:
            raise PatchError("resolved note escapes vault root") from exc
        write_atomic(destination, modified)
        writer = "atomic-large-file-fallback"
    verified = obsidian_read(note, vault_root)
    if sha256_text(verified) != sha256_text(modified):
        raise PatchError("post-write Obsidian readback does not match the intended note")
    return writer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-root", required=True, type=Path)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if shutil.which("obsidian") is None:
            raise PatchError("Obsidian CLI is unavailable")
        vault_root = args.vault_root.resolve()
        if not vault_root.is_dir():
            raise PatchError("vault root is not an existing directory")
        patch = json.loads(args.patch.read_text(encoding="utf-8"))
        note, entries = validate_patch(patch)
        original = obsidian_read(note, vault_root)
        if frontmatter_type(original) != "course-material":
            raise PatchError("target note frontmatter type must be course-material")
        modified, outcomes = apply_entries(original, entries)
        writer = "dry-run"
        if not args.dry_run and modified != original:
            writer = write_note(note, original, modified, vault_root)
        print(
            json.dumps(
                {
                    "ok": True,
                    "note": note,
                    "writer": writer,
                    "before_sha256": sha256_text(original),
                    "after_sha256": sha256_text(modified),
                    "outcomes": outcomes,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, PatchError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
