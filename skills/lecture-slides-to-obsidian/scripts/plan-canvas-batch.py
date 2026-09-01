#!/usr/bin/env python3
"""Validate and plan one-subagent-per-document Canvas batch delegation."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


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


def plan_batch(manifest: dict, max_parallel: int) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise BatchPlanError("batch manifest must be an object with schema_version 1")
    items = manifest.get("items")
    if not isinstance(items, list) or not items:
        raise BatchPlanError("batch manifest items must contain at least one document")
    if not isinstance(max_parallel, int) or max_parallel < 1:
        raise BatchPlanError("max_parallel must be a positive integer")

    required = {"id", "note", "recall_model", "canvas", "staging", "assets", "profile", "overwrite"}
    ids = set()
    unique_paths = {key: set() for key in ("note", "recall_model", "canvas", "staging", "assets")}
    normalized = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise BatchPlanError(f"items[{index}] must be an object")
        missing = sorted(required - item.keys())
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

    count = len(normalized)
    author_parallelism = min(max_parallel, count)
    waves = [
        [item["id"] for item in normalized[start : start + author_parallelism]]
        for start in range(0, count, author_parallelism)
    ]
    return {
        "schema_version": 1,
        "item_count": count,
        "spawn_required": count >= 2,
        "strategy": "one-subagent-per-document" if count >= 2 else "direct-or-single-subagent",
        "prompt_template": "skills/obsidian-canvas-designer/templates/delegated-task.md",
        "subagent_tasks": [
            {
                "id": item["id"],
                "note": item["note"],
                "recall_model": item["recall_model"],
                "canvas": item["canvas"],
                "staging": item["staging"],
                "assets": item["assets"],
                "profile": item["profile"],
                "overwrite": item["overwrite"],
                "phase_a_return": "READY_FOR_RENDER",
            }
            for item in normalized
        ],
        "authoring_parallelism": author_parallelism,
        "authoring_waves": waves,
        "renderer_parallelism": 1,
        "renderer_order": [item["id"] for item in normalized],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--max-parallel", required=True, type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        plan = plan_batch(manifest, args.max_parallel)
        if args.output is not None:
            write_json_atomic(args.output.resolve(), plan)
            response = {
                "plan": str(args.output.resolve()),
                "item_count": plan["item_count"],
                "spawn_required": plan["spawn_required"],
                "authoring_waves": plan["authoring_waves"],
                "renderer_parallelism": plan["renderer_parallelism"],
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
