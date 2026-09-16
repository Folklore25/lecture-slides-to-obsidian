#!/usr/bin/env python3
"""Plan one-subagent-per-file conversion dispatch.

Two or more source files in one request are dispatched to isolated subagents. The main
Agent keeps the shared state: course routing and the registry are resolved once, before
dispatch, so parallel workers cannot race on them.

Canvas is deliberately outside the fan-out. It is a single exclusive lane owned by the
main Agent, because Canvas QA drives the local Obsidian GUI.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


PROFILES = ("lecture-notes", "policy-document", "paper")
REQUIRED_FIELDS = ("id", "source", "document_folder", "staging", "profile")


class BatchPlanError(RuntimeError):
    pass


def inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


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


def plan_batch(manifest: dict, max_parallel: int, vault_root: Path | None = None) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise BatchPlanError("conversion batch manifest must be an object with schema_version 1")
    items = manifest.get("items")
    if not isinstance(items, list) or not items:
        raise BatchPlanError("conversion batch items must contain at least one source file")
    if not isinstance(max_parallel, int) or max_parallel < 1:
        raise BatchPlanError("max_parallel must be a positive integer")

    ids: set[str] = set()
    unique_paths = {key: set() for key in ("source", "document_folder", "staging")}
    normalized: list[dict] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise BatchPlanError(f"items[{index}] must be an object")
        missing = sorted(set(REQUIRED_FIELDS) - item.keys())
        if missing:
            raise BatchPlanError(f"items[{index}] missing fields: {', '.join(missing)}")
        item_id = item["id"]
        if not isinstance(item_id, str) or not item_id or item_id in ids:
            raise BatchPlanError(f"items[{index}].id must be a unique non-empty string")
        ids.add(item_id)
        profile = item["profile"]
        if profile not in PROFILES:
            raise BatchPlanError(f"items[{index}].profile is unsupported: {profile!r}")
        for key in unique_paths:
            value = item[key]
            if not isinstance(value, str) or not value:
                raise BatchPlanError(f"items[{index}].{key} must be a path string")
            resolved = str(Path(value).resolve())
            if resolved in unique_paths[key]:
                raise BatchPlanError(f"items[{index}].{key} collides with another file: {value}")
            unique_paths[key].add(resolved)
        if vault_root is not None:
            source = Path(item["source"])
            document_folder = Path(item["document_folder"])
            staging = Path(item["staging"])
            if inside(source, vault_root):
                raise BatchPlanError(f"items[{index}].source must stay outside the vault: {item['source']}")
            if not inside(document_folder, vault_root):
                raise BatchPlanError(
                    f"items[{index}].document_folder must resolve inside the vault: {item['document_folder']}"
                )
            if inside(staging, vault_root):
                raise BatchPlanError(f"items[{index}].staging must stay outside the vault: {item['staging']}")
        normalized.append(item)

    count = len(normalized)
    dispatch_required = count >= 2
    parallelism = min(max_parallel, count)
    waves = [
        [item["id"] for item in normalized[start : start + parallelism]]
        for start in range(0, count, parallelism)
    ]
    return {
        "schema_version": 1,
        "file_count": count,
        "dispatch_required": dispatch_required,
        "strategy": "one-subagent-per-file" if dispatch_required else "direct",
        "parallelism": parallelism,
        "waves": waves,
        "shared_state_owner": "main-agent",
        "shared_state": ["course-routing", "course-registry", "semester-resolution"],
        "canvas_lane": {
            "owner": "main-agent",
            "parallelism": 1,
            "exclusive_resource": "obsidian-app-gui",
            "phase": "after-conversion",
            "reason": "Canvas QA drives the local Obsidian GUI; concurrent Canvas work conflicts",
        },
        "isolation_verified": True,
        "subagent_tasks": [
            {
                "id": item["id"],
                "source": item["source"],
                "document_folder": item["document_folder"],
                "staging": item["staging"],
                "profile": item["profile"],
                "returns": "note, note-plan.json, page-ledger.json, assets, package validation evidence",
                "must_not": "build or check a Canvas",
            }
            for item in normalized
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--max-parallel", required=True, type=int)
    parser.add_argument("--vault-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        vault_root = args.vault_root.resolve() if args.vault_root else None
        plan = plan_batch(manifest, args.max_parallel, vault_root)
        if args.output is not None:
            write_json_atomic(args.output.resolve(), plan)
            response = {
                "plan": str(args.output.resolve()),
                "file_count": plan["file_count"],
                "dispatch_required": plan["dispatch_required"],
                "parallelism": plan["parallelism"],
                "waves": plan["waves"],
                "shared_state_owner": plan["shared_state_owner"],
                "canvas_lane": plan["canvas_lane"],
            }
        else:
            response = plan
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, BatchPlanError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
