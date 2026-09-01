#!/usr/bin/env python3
"""Validate a teacher-ASR enrichment plan and emit an insertion patch."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path


KINDS = {"explanation", "example", "emphasis", "correction", "boundary", "question-answer", "logistics"}
NOVELTY = {
    "new-explanation", "new-example", "new-emphasis", "correction",
    "boundary-condition", "question-answer", "new-logistics",
}
CONFIDENCE = {"high", "medium", "low"}
ENTRY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,80}$")


class PlanError(RuntimeError):
    pass


def normalize_text(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold()).strip()


def validate_plan(plan: dict) -> tuple[dict, list[dict]]:
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise PlanError("plan must be an object with schema_version 1")
    note = plan.get("note")
    asr_source = plan.get("asr_source")
    if not isinstance(note, str) or not note.endswith(".md") or Path(note).is_absolute() or ".." in Path(note).parts:
        raise PlanError("note must be a vault-relative Markdown path")
    if not isinstance(asr_source, str) or not asr_source.strip():
        raise PlanError("asr_source is required")
    entries = plan.get("entries")
    if not isinstance(entries, list):
        raise PlanError("entries must be an array")
    if not entries:
        reason = plan.get("no_additions_reason")
        if not isinstance(reason, str) or not reason.strip():
            raise PlanError("an empty plan requires no_additions_reason")
        return {"schema_version": 1, "note": note, "entries": []}, []

    seen_ids = set()
    seen_bodies = set()
    apply_entries = []
    review_entries = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise PlanError(f"entries[{index}] must be an object")
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not ENTRY_ID.fullmatch(entry_id) or entry_id in seen_ids:
            raise PlanError(f"entries[{index}].id must be unique and URL-safe")
        seen_ids.add(entry_id)
        if entry.get("actor") != "teacher" or entry.get("kind") not in KINDS:
            raise PlanError(f"entries[{index}] must use actor=teacher and an allowed teacher kind")
        if entry.get("target_level") not in {2, 3} or not isinstance(entry.get("target_heading"), str):
            raise PlanError(f"entries[{index}] needs an exact H2/H3 target")
        body = entry.get("body")
        evidence = entry.get("evidence")
        anchor = entry.get("source_anchor")
        if not isinstance(body, str) or not 8 <= len(body.strip()) <= 2000:
            raise PlanError(f"entries[{index}].body must contain 8..2000 characters")
        if not isinstance(evidence, str) or not 3 <= len(evidence.strip()) <= 500:
            raise PlanError(f"entries[{index}].evidence must contain 3..500 characters")
        if not isinstance(anchor, str) or not anchor.strip():
            raise PlanError(f"entries[{index}].source_anchor is required")
        if entry.get("novelty_basis") not in NOVELTY:
            raise PlanError(f"entries[{index}].novelty_basis is unsupported")
        confidence = entry.get("confidence")
        if confidence not in CONFIDENCE:
            raise PlanError(f"entries[{index}].confidence must be high, medium, or low")
        normalized_body = normalize_text(body)
        if normalized_body in seen_bodies:
            raise PlanError(f"entries[{index}] duplicates another planned addition")
        seen_bodies.add(normalized_body)
        apply_flag = entry.get("apply") is True
        if confidence == "low" and apply_flag:
            raise PlanError(f"entries[{index}] is low-confidence and cannot be applied")
        clean = {
            "id": entry_id,
            "actor": "teacher",
            "kind": entry["kind"],
            "target_heading": entry["target_heading"].strip(),
            "target_level": entry["target_level"],
            "body": body.strip(),
            "source_anchor": anchor.strip(),
            "confidence": confidence,
            "routing_status": entry.get("routing_status", "matched"),
        }
        if apply_flag:
            apply_entries.append(clean)
        else:
            review_entries.append({**clean, "evidence": evidence.strip(), "novelty_basis": entry["novelty_basis"]})
    return {"schema_version": 1, "note": note, "entries": apply_entries}, review_entries


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
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-patch", type=Path)
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        patch, review = validate_plan(plan)
        if args.output_patch is not None:
            write_json_atomic(args.output_patch.resolve(), patch)
        print(
            json.dumps(
                {
                    "ok": True,
                    "apply_count": len(patch["entries"]),
                    "review_count": len(review),
                    "output_patch": str(args.output_patch.resolve()) if args.output_patch else None,
                    "review_entries": review,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, PlanError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
