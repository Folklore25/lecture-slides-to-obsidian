#!/usr/bin/env python3
"""Validate per-Canvas isolation and describe the lease-guarded Canvas lane.

Canvas work is never fanned out. Canvas QA drives the local Obsidian GUI through
`canvas-render-qa.py`, so two Canvas tasks running at the same time fight over one
application. The lane therefore has parallelism 1 and is owned by the main Agent,
which runs one Canvas to completion before starting the next.

This planner validates that every Canvas task has its own isolated paths and returns the
order in which the main Agent must process them. It creates no agents.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


REQUIRED_FIELDS = (
    "id", "note", "recall_model", "canvas", "staging", "assets", "profile", "overwrite"
)
UNIQUE_PATH_FIELDS = ("note", "recall_model", "canvas", "staging", "assets")
GUI_LEASE_NAME = "obsidian-gui"
GUI_LEASE_TOOL = "scripts/obsidian-gui-lock.py"


class BatchPlanError(RuntimeError):
    pass


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


def plan_batch(manifest: dict) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise BatchPlanError("canvas batch manifest must be an object with schema_version 1")
    items = manifest.get("items")
    if not isinstance(items, list) or not items:
        raise BatchPlanError("canvas batch items must contain at least one Canvas")

    ids: set[str] = set()
    unique_paths = {key: set() for key in UNIQUE_PATH_FIELDS}
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
        for key in unique_paths:
            value = item[key]
            if not isinstance(value, str) or not value:
                raise BatchPlanError(f"items[{index}].{key} must be a path string")
            resolved = str(Path(value).resolve())
            if resolved in unique_paths[key]:
                raise BatchPlanError(f"items[{index}].{key} collides with another task: {value}")
            unique_paths[key].add(resolved)
        normalized.append(item)

    order = [item["id"] for item in normalized]
    return {
        "schema_version": 1,
        "item_count": len(normalized),
        "canvas_lane": {
            "authoring_parallelism": "unbounded",
            "dom_step_concurrency": 1,
            "dom_step_guard": "exclusive-lease",
            "lease_name": GUI_LEASE_NAME,
            "lease_tool": GUI_LEASE_TOOL,
            "focus_required": False,
            "queues_instead_of_failing": True,
            "order": order,
        },
        "merge_forbidden": True,
        "isolation_verified": True,
        "prompt_template": "skills/obsidian-canvas-designer/templates/delegated-task.md",
        "tasks": [
            {
                "id": item["id"],
                "note": item["note"],
                "recall_model": item["recall_model"],
                "canvas": item["canvas"],
                "staging": item["staging"],
                "assets": item["assets"],
                "profile": item["profile"],
                "overwrite": item["overwrite"],
            }
            for item in normalized
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        plan = plan_batch(manifest)
        if args.output is not None:
            write_json_atomic(args.output.resolve(), plan)
            response = {
                "plan": str(args.output.resolve()),
                "item_count": plan["item_count"],
                "authoring_parallelism": plan["canvas_lane"]["authoring_parallelism"],
                "dom_step_guard": plan["canvas_lane"]["dom_step_guard"],
                "lease_name": plan["canvas_lane"]["lease_name"],
                "process_order": plan["canvas_lane"]["order"],
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
