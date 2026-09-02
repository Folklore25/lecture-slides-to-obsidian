#!/usr/bin/env python3
"""Measure or verify text-card readability in the running Obsidian renderer."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


DEFAULT_PROFILE = Path(__file__).resolve().parent.parent / "config/render-profile.mbp14-composer.json"
OVERVIEW_MARKER = "<!-- recall-map: overview -->"


class RenderQaError(RuntimeError):
    pass


def inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rounded_required_height(
    max_child_bottom: float,
    vertical_chrome_px: int,
    safety_margin_px: int,
    round_to_px: int,
) -> int:
    raw = max_child_bottom + vertical_chrome_px + safety_margin_px
    return int(math.ceil(raw / round_to_px) * round_to_px)


def contains(group: dict, node: dict) -> bool:
    return (
        node["x"] >= group["x"]
        and node["y"] >= group["y"]
        and node["x"] + node["width"] <= group["x"] + group["width"]
        and node["y"] + node["height"] <= group["y"] + group["height"]
    )


def top_lane_clearance(canvas_data: dict) -> int | None:
    nodes = canvas_data.get("nodes", [])
    groups = [node for node in nodes if isinstance(node, dict) and node.get("type") == "group"]
    overview = [
        node for node in nodes
        if isinstance(node, dict)
        and node.get("type") == "text"
        and OVERVIEW_MARKER in node.get("text", "")
    ]
    outside_files = [
        node for node in nodes
        if isinstance(node, dict)
        and node.get("type") == "file"
        and not any(contains(group, node) for group in groups)
    ]
    if not groups or not overview:
        return None
    top_lane_bottom = max(node["y"] + node["height"] for node in overview + outside_files)
    return min(group["y"] for group in groups) - top_lane_bottom


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


def run_cli(arguments: list[str], cwd: Path) -> str:
    result = subprocess.run(arguments, cwd=cwd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise RenderQaError(f"Obsidian CLI failed: {message}")
    return result.stdout.strip()


def parse_eval_json(output: str) -> dict:
    payload = output.strip()
    if payload.startswith("=>"):
        payload = payload[2:].strip()
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RenderQaError(f"Obsidian eval did not return JSON: {payload[:240]}") from exc
    if not isinstance(value, dict):
        raise RenderQaError("Obsidian eval returned a non-object result")
    return value


def obsidian_eval(javascript: str, vault_root: Path) -> dict:
    output = run_cli(["obsidian", "eval", f"code={javascript}"], vault_root)
    return parse_eval_json(output)


def split_version(output: str) -> tuple[str, str | None]:
    first_line = output.splitlines()[0].strip()
    parts = first_line.split("(installer ", 1)
    app_version = parts[0].strip()
    installer = parts[1].rstrip(")") if len(parts) == 2 else None
    return app_version, installer


def environment_errors(profile: dict, environment: dict) -> list[str]:
    comparisons = {
        "obsidian_version": environment.get("obsidian_version"),
        "installer_version": environment.get("installer_version"),
        "screen_css_width": environment.get("screen_css_width"),
        "screen_css_height": environment.get("screen_css_height"),
        "device_pixel_ratio": environment.get("device_pixel_ratio"),
        "theme": environment.get("theme"),
        "base_font_size": environment.get("base_font_size"),
        "canvas_font_size_px": environment.get("canvas_font_size_px"),
        "canvas_line_height_px": environment.get("canvas_line_height_px"),
        "sidebar_font_size_px": environment.get("sidebar_font_size_px"),
    }
    errors = []
    for key, actual in comparisons.items():
        expected = profile.get(key)
        if isinstance(expected, float) and isinstance(actual, (int, float)):
            matches = abs(expected - float(actual)) < 0.05
        else:
            matches = expected == actual
        if not matches:
            errors.append(f"render profile mismatch for {key}: expected {expected!r}, found {actual!r}")
    if profile.get("requires_foreground") and not environment.get("document_has_focus"):
        errors.append("Obsidian must be foreground and focused during DOM measurement")
    return errors


def setup_javascript(canvas_path: str) -> str:
    target = json.dumps(canvas_path)
    return f"""(()=>{{
const target={target};
const leaf=app.workspace.getLeavesOfType('canvas').find(l=>l.view?.file?.path===target);
if(!leaf?.view?.canvas) throw new Error('Canvas view not found: '+target);
const canvas=leaf.view.canvas;
let mounted=0;
for(const node of canvas.nodes.values()){{
  if(typeof node.text!=='string') continue;
  node.attach();
  node.render();
  node.mountContent();
  node.child?.set(node.text);
  if(node.isContentMounted) mounted++;
}}
return JSON.stringify({{mounted,textNodes:[...canvas.nodes.values()].filter(n=>typeof n.text==='string').length}});
}})()"""


def measure_javascript(canvas_path: str) -> str:
    target = json.dumps(canvas_path)
    return f"""(()=>{{
const target={target};
const leaf=app.workspace.getLeavesOfType('canvas').find(l=>l.view?.file?.path===target);
if(!leaf?.view?.canvas) throw new Error('Canvas view not found: '+target);
const canvas=leaf.view.canvas;
const nodes=[];
for(const node of canvas.nodes.values()){{
  if(typeof node.text!=='string') continue;
  const content=node.contentEl;
  const sizer=content?.querySelector('.markdown-preview-sizer');
  if(!node.isContentMounted||!sizer) throw new Error('Text node was not rendered: '+node.id);
  const children=[...sizer.children].filter(el=>!el.classList.contains('markdown-preview-pusher'));
  if(children.length===0) throw new Error('Rendered Markdown children are missing: '+node.id);
  const maxChildBottom=Math.max(0,...children.map(el=>
    el.offsetTop+el.offsetHeight+parseFloat(getComputedStyle(el).marginBottom||'0')
  ));
  if(maxChildBottom<=0) throw new Error('Rendered Markdown height is zero: '+node.id);
  nodes.push({{
    id:node.id,
    text:node.text,
    width:node.width,
    height:node.height,
    max_child_bottom:Math.ceil(maxChildBottom),
    font_size_px:parseFloat(getComputedStyle(sizer).fontSize),
    line_height_px:parseFloat(getComputedStyle(sizer).lineHeight)
  }});
}}
const firstSizer=leaf.view.canvas.canvasEl.querySelector('.markdown-preview-sizer');
return JSON.stringify({{
  screen_css_width:screen.width,
  screen_css_height:screen.height,
  device_pixel_ratio:window.devicePixelRatio,
  window_css_width:window.innerWidth,
  window_css_height:window.innerHeight,
  theme:app.vault.getConfig('cssTheme')||'default',
  base_font_size:app.vault.getConfig('baseFontSize'),
  canvas_font_size_px:firstSizer?parseFloat(getComputedStyle(firstSizer).fontSize):null,
  canvas_line_height_px:firstSizer?parseFloat(getComputedStyle(firstSizer).lineHeight):null,
  sidebar_font_size_px:(()=>{{const el=document.querySelector('.nav-file-title');return el?parseFloat(getComputedStyle(el).fontSize):null;}})(),
  document_has_focus:document.hasFocus(),
  nodes
}});
}})()"""


def set_reading_view(canvas_path: str, vault_root: Path, reading_zoom: float) -> dict:
    target = json.dumps(canvas_path)
    zoom = json.dumps(reading_zoom)
    javascript = f"""(()=>{{
const target={target};
const leaf=app.workspace.getLeavesOfType('canvas').find(l=>l.view?.file?.path===target);
if(!leaf?.view?.canvas) throw new Error('Canvas view not found: '+target);
const canvas=leaf.view.canvas;
const overview=[...canvas.nodes.values()].find(n=>typeof n.text==='string'&&n.text.includes('<!-- recall-map: overview -->'));
const anchor=overview||[...canvas.nodes.values()].find(n=>typeof n.text==='string');
if(!anchor) throw new Error('No text node available for reading viewport');
canvas.setViewport(anchor.x+anchor.width/2,anchor.y+anchor.height/2,{zoom});
return JSON.stringify({{zoom:canvas.zoom,anchor:anchor.id}});
}})()"""
    return obsidian_eval(javascript, vault_root)


def measure_canvas(canvas: Path, vault_root: Path, profile: dict, mode: str) -> dict:
    relative = canvas.relative_to(vault_root).as_posix()
    run_cli(["obsidian", "open", f"path={relative}"], vault_root)
    if sys.platform == "darwin":
        subprocess.run(["open", "-a", "Obsidian"], check=False, capture_output=True, text=True)
    wait_seconds = profile.get("render_wait_ms", 800) / 1000
    time.sleep(wait_seconds)
    setup = obsidian_eval(setup_javascript(relative), vault_root)
    if setup.get("mounted") != setup.get("textNodes"):
        raise RenderQaError(
            f"only {setup.get('mounted')} of {setup.get('textNodes')} text nodes mounted in Obsidian"
        )
    time.sleep(wait_seconds)
    measured = obsidian_eval(measure_javascript(relative), vault_root)
    version_output = run_cli(["obsidian", "version"], vault_root)
    app_version, installer_version = split_version(version_output)
    measured["obsidian_version"] = app_version
    measured["installer_version"] = installer_version
    if mode == "check":
        measured["reading_view"] = set_reading_view(relative, vault_root, profile["reading_zoom"])
    return measured


def build_result(canvas: Path, profile: dict, measured: dict, mode: str) -> dict:
    env_errors = environment_errors(profile, measured)
    canvas_data = json.loads(canvas.read_text(encoding="utf-8"))
    top_gap = top_lane_clearance(canvas_data)
    layout_errors = []
    minimum_top_gap = profile.get("top_lane_to_modules_gap_px", 80)
    if mode == "check":
        if top_gap is None:
            layout_errors.append("top orientation lane or learning-module groups are missing")
        elif top_gap < minimum_top_gap:
            layout_errors.append(
                f"top orientation lane has only {top_gap}px before learning modules; "
                f"requires at least {minimum_top_gap}px"
            )
    records = []
    for node in measured.get("nodes", []):
        required = rounded_required_height(
            node["max_child_bottom"],
            profile["vertical_chrome_px"],
            profile["safety_margin_px"],
            profile["round_to_px"],
        )
        exact = math.ceil(node["max_child_bottom"] + profile["vertical_chrome_px"])
        records.append(
            {
                "id": node["id"],
                "width": node["width"],
                "current_height": node["height"],
                "max_child_bottom": node["max_child_bottom"],
                "exact_required_height": exact,
                "required_height": required,
                "headroom": node["height"] - exact,
                "clipped": node["height"] < exact,
                "passes_profile_margin": node["height"] >= required,
                "text_sha256": sha256_text(node["text"]),
            }
        )
    clipped = [record["id"] for record in records if record["clipped"]]
    under_margin = [record["id"] for record in records if not record["passes_profile_margin"]]
    actual_zoom = profile["reading_zoom"]
    if mode == "check":
        actual_zoom = measured.get("reading_view", {}).get("zoom")
        if not isinstance(actual_zoom, (int, float)) or abs(actual_zoom - profile["reading_zoom"]) > 0.001:
            env_errors.append(
                f"reading viewport mismatch: expected zoom {profile['reading_zoom']!r}, found {actual_zoom!r}"
            )
            actual_zoom = profile["reading_zoom"] if not isinstance(actual_zoom, (int, float)) else actual_zoom
    effective_font = measured.get("canvas_font_size_px", 0) * (2 ** actual_zoom)
    readable_scale = effective_font >= profile["minimum_effective_font_px"]
    valid = not env_errors and not layout_errors and readable_scale and (mode == "measure" or not under_margin)
    return {
        "schema_version": 1,
        "mode": mode,
        "profile_id": profile["profile_id"],
        "canvas": str(canvas),
        "canvas_sha256": sha256_file(canvas),
        "environment": {key: value for key, value in measured.items() if key != "nodes"},
        "environment_errors": env_errors,
        "layout_errors": layout_errors,
        "top_lane_to_modules_gap": top_gap,
        "minimum_top_lane_to_modules_gap": minimum_top_gap,
        "nodes": records,
        "clipped_nodes": clipped,
        "nodes_below_profile_margin": under_margin,
        "reading_zoom": actual_zoom,
        "effective_font_size_px": effective_font,
        "minimum_effective_font_px": profile["minimum_effective_font_px"],
        "reading_scale_pass": readable_scale,
        "measurement_complete": bool(records) and not env_errors,
        "valid": valid,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("measure", "check"))
    parser.add_argument("--canvas", required=True, type=Path)
    parser.add_argument("--vault-root", required=True, type=Path)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        if shutil.which("obsidian") is None:
            raise RenderQaError("Obsidian CLI is not installed or not on PATH")
        canvas = args.canvas.resolve()
        vault_root = args.vault_root.resolve()
        if not canvas.is_file() or not inside(canvas, vault_root):
            raise RenderQaError("--canvas must be an existing file inside --vault-root")
        if canvas.suffix != ".canvas":
            raise RenderQaError("--canvas must use the .canvas extension")
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        if profile.get("schema_version") != 1:
            raise RenderQaError("render profile must use schema_version 1")
        if args.output is not None and inside(args.output.resolve(), vault_root):
            raise RenderQaError("render QA output must remain outside the vault")
        measured = measure_canvas(canvas, vault_root, profile, args.mode)
        result = build_result(canvas, profile, measured, args.mode)
        if args.output is not None:
            write_json_atomic(args.output.resolve(), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    except (OSError, json.JSONDecodeError, RenderQaError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
