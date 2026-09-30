#!/usr/bin/env python3
"""Canonicalize delivered visual assets to WebP and rewrite every reference to them.

A slide deck is mostly whitespace, and a full-page render is several times larger
than the figure inside it. Nothing in the extraction path shrinks anything, so a
converted course fills the vault with multi-megabyte PNGs that the reader only
ever sees at 420px. This script closes that gap deterministically: it re-encodes
every delivered raster to WebP, caps the longest edge, and keeps the notes, the
Canvas file nodes, and the page ledger pointing at the files that actually exist.

Inputs
  <document-folder|assets-dir>
                                 positional. A document folder must contain assets/.
  --vault-root <root>            required. Every .md and .canvas under it is the
                                 reference surface, and a converted original is
                                 unlinked only after this scan proves it is unused.
  --all-assets                   process every assets/ directory under --vault-root
                                 instead of the single document folder.
  --references <path>            extra text file to rewrite (repeatable). Notes and
                                 Canvas files inside the document folder are found
                                 automatically; pass note-plan.json or any other file
                                 that names an asset explicitly.
  --ledger <path>                page-ledger.json whose visual asset names follow the
                                 files, so the ledger and assets/ stay cross-checkable.
  --max-edge <px>                longest-edge cap for a delivered raster. Default 1600.
  --quality <q>                  WebP quality, 1-100. Default 80.
  --cwebp <path>                 explicit encoder binary. Default: cwebp on PATH.
  --report <path>                JSON report destination. Default: stdout.
  --force                        deliver a uniform WebP folder even when one asset
                                 would grow. Without it, a file that WebP cannot shrink
                                 keeps its current bytes and is reported under kept.
  --dry-run                      encode to a temporary file to measure the result,
                                 report it, and change nothing in the vault.

Outputs
  A JSON report with schema_version, the resolved policy, converted/kept/
  retained_originals/failed entries, per-directory and total byte totals, and
  warnings. The report is deterministic apart from the measured byte counts.

Exit codes
  0 every asset is a delivered WebP within the edge cap (warnings may be present)
  1 a hard failure: missing encoder, failed encode, name collision, unusable input
  2 usage error

Token transport, network, secrets
  None. No token is read, no network call is made, nothing outside --vault-root is
  read, and no absolute path from the source document can reach the report.

Overwrite rules
  A pre-existing .webp target whose bytes differ is a collision and fails the run;
  identical bytes count as already delivered. The original is unlinked only after
  no .md or .canvas under --vault-root still references it, so a missed reference
  costs bytes rather than a broken embed. --dry-run, a failed encode, and a
  retained original all leave the input file untouched.

Raster policy
  .png, .jpg, .jpeg, and .bmp are re-encoded. .webp is kept when it is already
  within the edge cap and re-encoded only when it is not. .gif and .svg are passed
  through: animation and vector art do not survive a WebP re-encode intact.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

DELIVERED_EXTENSION = ".webp"
RECODE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}
PASSTHROUGH_EXTENSIONS = {".gif", ".svg"}
REFERENCE_SUFFIXES = {".md", ".canvas"}
DEFAULT_MAX_EDGE = 1600
DEFAULT_QUALITY = 80
MIN_DELIVERED_EDGE = 320
SKIPPED_DIRECTORIES = {".obsidian", ".trash", ".git", "node_modules"}


class OptimizeError(RuntimeError):
    """A hard failure that must stop the run instead of degrading the delivery."""


def validator_image_dimensions():
    """Reuse the delivery validator's header parser so both agree on what a pixel is."""
    script = Path(__file__).resolve().with_name("validate-output.py")
    spec = spec_from_file_location("validate_output_dimensions", script)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise OptimizeError(f"cannot load the image dimension reader from {script}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.image_dimensions


def resolve_assets_dir(target: Path) -> Path:
    if target.name == "assets" and target.is_dir():
        return target
    candidate = target / "assets"
    if candidate.is_dir():
        return candidate
    raise OptimizeError(f"no assets directory at {target}")


def collect_assets_dirs(target: Path, vault_root: Path, all_assets: bool) -> list[Path]:
    if not all_assets:
        return [resolve_assets_dir(target)]
    found = sorted(
        path
        for path in vault_root.rglob("assets")
        if path.is_dir() and not any(part in SKIPPED_DIRECTORIES for part in path.parts)
    )
    if not found:
        raise OptimizeError(f"no assets directory found under {vault_root}")
    return found


def resize_arguments(width: int, height: int, max_edge: int) -> list[str]:
    """cwebp takes an explicit target box; a zero side follows the aspect ratio."""
    if max(width, height) <= max_edge:
        return []
    if width >= height:
        return ["-resize", str(max_edge), "0"]
    return ["-resize", "0", str(max_edge)]


def encode_to_webp(
    encoder: str, source: Path, destination: Path, quality: int, resize: list[str]
) -> None:
    command = [
        encoder,
        "-quiet",
        "-q",
        str(quality),
        "-metadata",
        "none",
        *resize,
        "-o",
        str(destination),
        str(source),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not destination.is_file() or destination.stat().st_size == 0:
        raise OptimizeError(
            f"{source.name}: WebP encoding failed ({result.returncode}): "
            f"{result.stderr.strip() or 'no encoder output'}"
        )


def filecmp_identical(left: Path, right: Path) -> bool:
    return filecmp.cmp(left, right, shallow=False)


def owning_assets_dir(reference_file: Path, assets_dirs: list[Path]) -> Path | None:
    parents = reference_file.resolve().parent
    for assets_dir in assets_dirs:
        if parents == assets_dir.parent or assets_dir.parent in parents.parents:
            return assets_dir
    return None


def reference_pattern(name: str) -> re.Pattern[str]:
    escaped = re.escape(name)
    return re.compile(rf"assets/{escaped}|!\[\[\s*{escaped}(?=[|\]])")


def rewrite_text(text: str, mapping: dict[str, str]) -> str:
    for old, new in mapping.items():
        text = text.replace(f"assets/{old}", f"assets/{new}")
        text = re.sub(rf"(!\[\[\s*){re.escape(old)}(?=[|\]])", rf"\g<1>{new}", text)
    return text


def rewrite_json(value, mapping: dict[str, str]):
    if isinstance(value, str):
        if value in mapping:
            return mapping[value]
        if value.startswith("assets/") and value[len("assets/"):] in mapping:
            return "assets/" + mapping[value[len("assets/"):]]
        return value
    if isinstance(value, list):
        return [rewrite_json(item, mapping) for item in value]
    if isinstance(value, dict):
        return {key: rewrite_json(item, mapping) for key, item in value.items()}
    return value


def write_text_atomic(path: Path, text: str) -> None:
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), suffix=".rewrite")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def iter_reference_files(vault_root: Path) -> list[Path]:
    return sorted(
        path
        for path in vault_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in REFERENCE_SUFFIXES
        and not any(part in SKIPPED_DIRECTORIES for part in path.parts)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", type=Path, help="document folder or assets directory")
    parser.add_argument("--vault-root", type=Path, required=True, help="vault root to rewrite and scan")
    parser.add_argument("--all-assets", action="store_true", help="process every assets/ under the vault root")
    parser.add_argument("--references", type=Path, action="append", default=[], help="extra file to rewrite")
    parser.add_argument("--ledger", type=Path, help="page ledger whose asset names follow the files")
    parser.add_argument("--max-edge", type=int, default=DEFAULT_MAX_EDGE)
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    parser.add_argument("--cwebp", help="explicit cwebp binary")
    parser.add_argument("--report", type=Path, help="JSON report destination")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.quality <= 100:
        print("quality must be between 1 and 100", file=sys.stderr)
        return 2
    if args.max_edge < MIN_DELIVERED_EDGE:
        print(f"max-edge must be at least {MIN_DELIVERED_EDGE}px", file=sys.stderr)
        return 2

    vault_root = args.vault_root.resolve()
    if not vault_root.is_dir():
        print(f"vault root is not a directory: {vault_root}", file=sys.stderr)
        return 2

    encoder = args.cwebp or shutil.which("cwebp")
    if encoder is None:
        print(
            "cwebp is required to deliver WebP assets; install it with: brew install webp",
            file=sys.stderr,
        )
        return 1
    if not Path(encoder).is_file() or not os.access(encoder, os.X_OK):
        print(f"encoder is not an executable file: {encoder}", file=sys.stderr)
        return 1

    image_dimensions = validator_image_dimensions()
    try:
        assets_dirs = collect_assets_dirs(args.target, vault_root, args.all_assets)
    except OptimizeError as error:
        print(str(error), file=sys.stderr)
        return 1

    report: dict = {
        "schema_version": 1,
        "policy": {
            "format": DELIVERED_EXTENSION.lstrip("."),
            "max_edge": args.max_edge,
            "quality": args.quality,
            "force": args.force,
            "dry_run": args.dry_run,
        },
        "assets_directories": [str(path) for path in assets_dirs],
        "converted": [],
        "kept": [],
        "passthrough": [],
        "retained_originals": [],
        "failed": [],
        "rewritten_files": [],
        "warnings": [],
        "bytes_before": 0,
        "bytes_after": 0,
    }

    # 1. Encode first, so a reference is only rewritten once its target really exists.
    mapping: dict[str, str] = {}
    owners: dict[str, set[Path]] = {}
    pending_delete: list[tuple[Path, Path]] = []
    for assets_dir in assets_dirs:
        for source in sorted(assets_dir.iterdir()):
            if not source.is_file():
                continue
            extension = source.suffix.lower()
            if extension in PASSTHROUGH_EXTENSIONS:
                report["passthrough"].append(str(source.relative_to(assets_dir)))
                continue
            if extension not in RECODE_EXTENSIONS and extension != DELIVERED_EXTENSION:
                continue
            size = image_dimensions(source)
            if size is None:
                report["failed"].append(
                    {"asset": source.name, "reason": "unreadable image header"}
                )
                continue
            width, height = size
            before = source.stat().st_size
            report["bytes_before"] += before
            resize = resize_arguments(width, height, args.max_edge)
            if extension == DELIVERED_EXTENSION and not resize:
                report["kept"].append({"asset": source.name, "bytes": before, "dimensions": [width, height]})
                report["bytes_after"] += before
                continue

            target = source.with_suffix(DELIVERED_EXTENSION)
            # A delivered WebP that is still over the cap is re-encoded onto itself.
            in_place = target == source
            handle, temporary_name = tempfile.mkstemp(dir=str(assets_dir), suffix=DELIVERED_EXTENSION)
            os.close(handle)
            temporary = Path(temporary_name)
            try:
                encode_to_webp(encoder, source, temporary, args.quality, resize)
                after = temporary.stat().st_size
                if target.exists() and not in_place:
                    if filecmp_identical(target, temporary):
                        report["kept"].append(
                            {"asset": source.name, "bytes": before, "dimensions": [width, height]}
                        )
                        report["bytes_after"] += before
                        continue
                    raise OptimizeError(
                        f"standardized asset collision: {target.name} already exists with different bytes"
                    )
                if after >= before and not args.force:
                    report["kept"].append(
                        {
                            "asset": source.name,
                            "bytes": before,
                            "dimensions": [width, height],
                            "reason": "WebP would not be smaller than the original",
                        }
                    )
                    report["bytes_after"] += before
                    continue
                if args.dry_run:
                    report["converted"].append(
                        {
                            "asset": source.name,
                            "delivered_as": target.name,
                            "bytes_before": before,
                            "bytes_after": after,
                            "source_dimensions": [width, height],
                            "resized": bool(resize),
                        }
                    )
                    report["bytes_after"] += after
                    continue
                os.replace(temporary, target)
            except OptimizeError as error:
                report["failed"].append({"asset": source.name, "reason": str(error)})
                continue
            finally:
                if temporary.exists():
                    temporary.unlink()

            report["converted"].append(
                {
                    "asset": source.name,
                    "delivered_as": target.name,
                    "bytes_before": before,
                    "bytes_after": after,
                    "source_dimensions": [width, height],
                    "resized": bool(resize),
                    "forced": after >= before,
                }
            )
            report["bytes_after"] += after
            if not in_place:
                mapping[source.name] = target.name
                owners.setdefault(source.name, set()).add(assets_dir)
                pending_delete.append((source, target))

    if report["failed"]:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    # 2. Rewrite every reference in the vault, scoped to the assets directory that
    #    owns the file, so one course's foo.png never renames another course's foo.png.
    if mapping and not args.dry_run:
        scoped_files = [path.resolve() for path in args.references]
        scoped_files += [
            path.resolve()
            for assets_dir in assets_dirs
            for path in sorted(assets_dir.parent.iterdir())
            if path.is_file() and path.suffix.lower() in REFERENCE_SUFFIXES
        ]
        scoped_files += iter_reference_files(vault_root)
        for reference in dict.fromkeys(scoped_files):
            local = owning_assets_dir(reference, assets_dirs)
            applicable = {
                old: new
                for old, new in mapping.items()
                if local is not None and local in owners[old]
            }
            if local is None:
                applicable = {
                    old: new for old, new in mapping.items() if len(owners[old]) == 1
                }
                if not applicable and any(len(owners[old]) > 1 for old in mapping):
                    report["warnings"].append(
                        f"{reference.name} is outside every assets directory; an ambiguous asset "
                        "name in it was left untouched"
                    )
                    continue
            if not applicable:
                continue
            text = reference.read_text(encoding="utf-8")
            updated = rewrite_text(text, applicable)
            if updated != text:
                write_text_atomic(reference, updated)
                report["rewritten_files"].append(str(reference.relative_to(vault_root)))

    if args.ledger and mapping and not args.dry_run and args.ledger.is_file():
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        updated = rewrite_json(ledger, mapping)
        if updated != ledger:
            write_text_atomic(
                args.ledger, json.dumps(updated, ensure_ascii=False, indent=2) + "\n"
            )
            report["rewritten_files"].append(str(args.ledger))

    # 3. Unlink an original only when nothing in the vault still points at it.
    if pending_delete and not args.dry_run:
        survivors = {
            path: path.read_text(encoding="utf-8", errors="ignore")
            for path in iter_reference_files(vault_root)
        }
        for source, target in pending_delete:
            pattern = reference_pattern(source.name)
            holders = sorted(
                str(path.relative_to(vault_root))
                for path, text in survivors.items()
                if pattern.search(text)
            )
            if holders:
                report["retained_originals"].append(
                    {"asset": source.name, "still_referenced_by": holders}
                )
                report["warnings"].append(
                    f"{source.name} is still referenced by {', '.join(holders)}; both files kept"
                )
                report["bytes_after"] += source.stat().st_size
                continue
            source.unlink()

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
