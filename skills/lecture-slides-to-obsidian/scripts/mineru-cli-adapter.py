#!/usr/bin/env python3
"""Run the official mineru-open-api CLI and normalize its content-list JSON."""

from __future__ import annotations

import argparse
import filecmp
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class AdapterError(RuntimeError):
    pass


ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}


def load_token_store_module():
    path = Path(__file__).resolve().parent / "token-store.py"
    spec = importlib.util.spec_from_file_location("lecture_skill_token_store", path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise AdapterError("cannot load token-store.py")
    spec.loader.exec_module(module)
    return module


def text_span(value: str) -> list[dict]:
    return [{"type": "text", "content": value}]


def legacy_block_to_v2(block: dict) -> dict | None:
    block_type = block.get("type", "text")
    bbox = block.get("bbox")
    result: dict = {}
    if block_type == "text":
        text = str(block.get("text", "")).strip()
        if not text:
            return None
        level = block.get("text_level", 0)
        if isinstance(level, int) and level > 0:
            result = {"type": "title", "content": {"title_content": text_span(text), "level": level}}
        else:
            result = {"type": "paragraph", "content": {"paragraph_content": text_span(text)}}
    elif block_type == "equation":
        value = str(block.get("text") or block.get("latex") or "").strip()
        result = {"type": "equation_interline", "content": {"math_content": value}}
    elif block_type in {"image", "chart", "table"}:
        content = {key: value for key, value in block.items() if key not in {"type", "page_idx", "bbox"}}
        result = {"type": block_type, "content": content}
        if block.get("sub_type"):
            result["sub_type"] = block["sub_type"]
    elif block_type in {"list", "index"}:
        items = block.get("list_items") or block.get("text") or []
        if isinstance(items, str):
            items = [items]
        result = {"type": block_type, "content": {"list_items": items}}
    elif block_type in {"code", "algorithm"}:
        value = block.get("code_body") or block.get("text") or ""
        result = {"type": block_type, "content": {f"{block_type}_content": value}}
    else:
        auxiliary = {
            "header": "page_header",
            "footer": "page_footer",
            "aside_text": "page_aside_text",
            "page_footnote": "page_footnote",
            "page_number": "page_number",
        }
        mapped = auxiliary.get(block_type)
        if mapped:
            value = str(block.get("text") or "").strip()
            result = {"type": mapped, "content": {f"{mapped}_content": text_span(value)}}
        else:
            value = str(block.get("text") or "").strip()
            if not value:
                return None
            result = {"type": "paragraph", "content": {"paragraph_content": text_span(value)}}
    if bbox is not None:
        result["bbox"] = bbox
    return result


def legacy_content_list_to_pages(content_list: list[dict]) -> list[list[dict]]:
    if not isinstance(content_list, list):
        raise AdapterError("official CLI JSON output must be a content-list array")
    page_indices = [item.get("page_idx") for item in content_list if isinstance(item, dict)]
    valid_indices = [value for value in page_indices if isinstance(value, int) and value >= 0]
    if not valid_indices:
        raise AdapterError("content-list JSON has no valid page_idx values")
    pages: list[list[dict]] = [[] for _ in range(max(valid_indices) + 1)]
    for block in content_list:
        if not isinstance(block, dict):
            continue
        page_idx = block.get("page_idx")
        if not isinstance(page_idx, int) or page_idx < 0:
            raise AdapterError("content-list block is missing a valid page_idx")
        converted = legacy_block_to_v2(block)
        if converted:
            pages[page_idx].append(converted)
    return pages


def write_json_atomic(path: Path, value) -> None:
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


def run_extract(
    source: Path,
    output_dir: Path,
    token: str,
    language: str,
    is_ocr: bool,
    model: str = "vlm",
    timeout: int = 300,
    executable: str | None = None,
) -> dict:
    source = source.resolve()
    output_dir = output_dir.resolve()
    executable = executable or shutil.which("mineru-open-api")
    if not source.is_file():
        raise AdapterError("source file does not exist")
    if not token.strip():
        raise AdapterError("decrypted MinerU token is empty")
    if not language.strip():
        raise AdapterError("confirmed MinerU language is required")
    if timeout <= 0:
        raise AdapterError("timeout must be positive")
    if not executable:
        raise AdapterError("official mineru-open-api CLI was not found")
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        executable,
        "extract",
        str(source),
        "-o",
        str(output_dir) + os.sep,
        "-f",
        "md,json",
        "--model",
        model,
        "--language",
        language,
        "--formula=true",
        "--table=true",
        "--timeout",
        str(timeout),
    ]
    if is_ocr:
        command.append("--ocr")
    environment = os.environ.copy()
    environment["MINERU_TOKEN"] = token
    environment["MINERU_SOURCE"] = "lecture-slides-to-obsidian"
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env=environment,
        )
    finally:
        environment.pop("MINERU_TOKEN", None)
    stderr = result.stderr.replace(token, "[REDACTED]")
    stdout = result.stdout.replace(token, "[REDACTED]")
    if result.returncode != 0:
        raise AdapterError(f"mineru-open-api failed ({result.returncode}): {stderr.strip()}")

    base = source.stem
    markdown_path = output_dir / f"{base}.md"
    json_path = output_dir / f"{base}.json"
    if not markdown_path.is_file() or not json_path.is_file():
        raise AdapterError("official CLI did not produce the expected Markdown and JSON files")
    try:
        legacy = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AdapterError(f"official CLI JSON output is invalid: {exc}") from exc
    page_groups = legacy_content_list_to_pages(legacy)
    normalized_path = output_dir / f"{base}.content-list-v2.compat.json"
    write_json_atomic(normalized_path, page_groups)
    normalized_assets_dir = output_dir / "normalized-assets"
    asset_paths = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in ASSET_EXTENSIONS
        and normalized_assets_dir not in path.parents
    )
    normalized_assets: list[str] = []
    if asset_paths:
        normalized_assets_dir.mkdir(exist_ok=True)
    for asset in asset_paths:
        destination = normalized_assets_dir / asset.name
        if destination.exists() and not filecmp.cmp(asset, destination, shallow=False):
            raise AdapterError(f"asset basename collision: {asset.name}")
        if not destination.exists():
            shutil.copy2(asset, destination)
        normalized_assets.append(str(destination))
    return {
        "source_filename": source.name,
        "markdown": str(markdown_path),
        "legacy_content_list": str(json_path),
        "normalized_page_groups": str(normalized_path),
        "asset_candidates": [str(path.relative_to(output_dir)) for path in asset_paths],
        "normalized_assets_dir": str(normalized_assets_dir),
        "normalized_assets": normalized_assets,
        "page_count": len(page_groups),
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--language", required=True)
    parser.add_argument("--is-ocr", required=True, choices=("true", "false"))
    parser.add_argument("--model", default="vlm", choices=("vlm", "pipeline"))
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    try:
        token_store = load_token_store_module()
        token = token_store.load_token_auto()
        manifest = run_extract(
            args.source,
            args.output_dir,
            token,
            args.language,
            args.is_ocr == "true",
            args.model,
            args.timeout,
        )
    except (OSError, AdapterError, Exception) as exc:
        print(f"mineru-cli-adapter error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
