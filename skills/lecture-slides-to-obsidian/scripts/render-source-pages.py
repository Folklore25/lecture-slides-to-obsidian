#!/usr/bin/env python3
"""Render source pages into model-ready WebP images for native reading.

A PDF page rasterised at 150 DPI is a 2000x1125 PNG of roughly 1 MB, and the harness
sends an image inline as base64: 1.4 MB of request body per page, tens of megabytes
for one deck, which is what makes a gateway answer 413. The harness only re-encodes an
image when one side exceeds its 2000px cap, and when it does re-encode it tries PNG
first, so an oversized page can come back as a 2 MB PNG instead of a 120 KB WebP.

So the page is encoded once, here, at the resolution the model will actually receive:
WebP, both sides within the cap, no downscaling beyond it. The result is ~90% smaller
on the wire at identical pixel dimensions, and the harness passes it through untouched.

Inputs
  <source.pdf>                       the source document; it stays outside the vault
  --output-dir <dir>                 required. Staging, outside the vault.
  --pages <spec>                     "all" (default), "1-12", or "1,4,9-12"
  --dpi <n>                          render DPI ceiling, default 150. Lowered
                                     automatically so both sides fit --max-edge.
  --max-edge <px>                    longest-edge ceiling, default 2000. Keep it at
                                     or below the harness cap: a larger value only
                                     triggers the harness re-encode this script avoids.
  --quality <q>                      WebP quality 1-100, default 82
  --vault-root <root>                when given, the output directory must resolve
                                     outside it
  --report <path>                    JSON report destination
  --dry-run                          resolve pages, DPI, and dimensions; render nothing

Outputs
  <output-dir>/page-<PPP>.webp, 3-digit 1-based page numbers matching the page ledger.
  A JSON report with the resolved DPI, the per-page and total encoded bytes, the
  base64 request-body estimate, and a per-page budget used to size a read batch.

Exit codes
  0 every requested page rendered, verified, and within the edge ceiling
  1 a hard failure: missing tool, unreadable source, failed render, or an unverified page
  2 usage error

Token transport, network, secrets
  None. No token is read, no network call is made, and the source path never reaches
  the report. Nothing is written outside --output-dir.

Overwrite rules
  An existing page file with different bytes is a collision and fails the run;
  identical bytes count as already rendered. Temporary PNGs are removed as each page
  is encoded, so staging never holds a full PNG deck. --dry-run writes nothing.

What this script does not do
  It rasterises pages for a multimodal model to look at. It extracts no text, no
  tables, and no structure: reading the pages is the model's job, and MinerU remains
  the path for a model that cannot see them.
"""

from __future__ import annotations

import argparse
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
DEFAULT_DPI = 150
# The harness re-encodes an inline image whose side exceeds this, trying PNG first, so a
# larger value would make every page more expensive to send, not less.
HARNESS_MAX_EDGE = 2000
DEFAULT_QUALITY = 82
PAGE_NAME = re.compile(r"^page-(\d{3})\.webp$")


class RenderError(RuntimeError):
    """A hard failure that must stop the run instead of degrading the reading pass."""


def validator_image_dimensions():
    """Reuse the delivery validator's header parser so both agree on what a pixel is."""
    script = Path(__file__).resolve().with_name("validate-output.py")
    spec = spec_from_file_location("validate_output_dimensions", script)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RenderError(f"cannot load the image dimension reader from {script}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.image_dimensions


def require_tool(name: str, install: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RenderError(f"{name} is required to render source pages; install it with: {install}")
    return path


def parse_pages(spec: str, page_count: int) -> list[int]:
    text = spec.strip().lower()
    if text in {"all", "*", ""}:
        return list(range(1, page_count + 1))
    pages: set[int] = set()
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, _, end = chunk.partition("-")
            try:
                first, last = int(start), int(end)
            except ValueError as error:
                raise RenderError(f"unreadable page range: {chunk!r}") from error
            if first > last:
                first, last = last, first
            pages.update(range(first, last + 1))
        else:
            try:
                pages.add(int(chunk))
            except ValueError as error:
                raise RenderError(f"unreadable page number: {chunk!r}") from error
    if not pages:
        raise RenderError(f"no pages selected by {spec!r}")
    outside = sorted(page for page in pages if not 1 <= page <= page_count)
    if outside:
        raise RenderError(f"page numbers outside 1..{page_count}: {outside}")
    return sorted(pages)


def page_geometry(pdfinfo: str, source: Path) -> tuple[int, float, float]:
    result = subprocess.run([pdfinfo, str(source)], capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(f"pdfinfo could not read {source.name}: {result.stderr.strip()}")
    count = 0
    width = height = 0.0
    for line in result.stdout.splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        if key == "Pages":
            count = int(value)
        elif key == "Page size" and not width:
            numbers = re.findall(r"\d+(?:\.\d+)?", value)
            if len(numbers) >= 2:
                width, height = float(numbers[0]), float(numbers[1])
    if count <= 0 or width <= 0 or height <= 0:
        raise RenderError(f"{source.name} reported no usable page geometry")
    return count, width, height


def dpi_within(points: float, requested: int, max_edge: int) -> int:
    """Pick a DPI whose rendered page fits the ceiling on its longer side."""
    longest_inches = points / 72.0
    ceiling_dpi = int(max_edge / longest_inches)
    return max(1, min(requested, ceiling_dpi))


def resize_arguments(width: int, height: int, max_edge: int) -> list[str]:
    if max(width, height) <= max_edge:
        return []
    if width >= height:
        return ["-resize", str(max_edge), "0"]
    return ["-resize", "0", str(max_edge)]


def encode_page(cwebp: str, source: Path, target: Path, quality: int, resize: list[str]) -> None:
    result = subprocess.run(
        [cwebp, "-quiet", "-q", str(quality), "-metadata", "none", *resize, "-o", str(target), str(source)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not target.is_file() or target.stat().st_size == 0:
        raise RenderError(
            f"{source.name}: WebP encoding failed ({result.returncode}): "
            f"{result.stderr.strip() or 'no encoder output'}"
        )


def base64_size(size: int) -> int:
    return 4 * ((size + 2) // 3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="source PDF, outside the vault")
    parser.add_argument("--output-dir", type=Path, required=True, help="staging directory outside the vault")
    parser.add_argument("--pages", default="all")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    parser.add_argument("--max-edge", type=int, default=HARNESS_MAX_EDGE)
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    parser.add_argument("--vault-root", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.quality <= 100:
        print("quality must be between 1 and 100", file=sys.stderr)
        return 2
    if not 1 <= args.max_edge <= HARNESS_MAX_EDGE:
        print(
            f"max-edge must be between 1 and {HARNESS_MAX_EDGE}; a larger ceiling only makes the "
            "harness re-encode the page into a much larger PNG",
            file=sys.stderr,
        )
        return 2
    if args.dpi < 1:
        print("dpi must be positive", file=sys.stderr)
        return 2

    source = args.source.resolve()
    if not source.is_file():
        print(f"source document not found: {source}", file=sys.stderr)
        return 2
    if source.suffix.lower() != ".pdf":
        print(f"source must be a PDF, got {source.suffix or 'no extension'}", file=sys.stderr)
        return 2

    output_dir = args.output_dir.resolve()
    if args.vault_root is not None:
        vault_root = args.vault_root.resolve()
        if output_dir == vault_root or vault_root in output_dir.parents:
            print("output directory must stay outside the vault", file=sys.stderr)
            return 2

    try:
        pdfinfo = require_tool("pdfinfo", "brew install poppler")
        pdftoppm = require_tool("pdftoppm", "brew install poppler")
        cwebp = require_tool("cwebp", "brew install webp")
        image_dimensions = validator_image_dimensions()
        page_count, page_width, page_height = page_geometry(pdfinfo, source)
        pages = parse_pages(args.pages, page_count)
    except RenderError as error:
        print(str(error), file=sys.stderr)
        return 1

    dpi = dpi_within(max(page_width, page_height), args.dpi, args.max_edge)
    report: dict = {
        "schema_version": 1,
        "source_pages": page_count,
        "pages": pages,
        "policy": {
            "dpi": dpi,
            "max_edge": args.max_edge,
            "quality": args.quality,
            "format": DELIVERED_EXTENSION.lstrip("."),
            "dry_run": args.dry_run,
        },
        "rendered": [],
        "skipped": [],
        "failed": [],
        "bytes": 0,
        "base64_bytes": 0,
    }

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="page-render-") as scratch:
            for page in pages:
                prefix = Path(scratch) / f"page-{page:03d}"
                raster = subprocess.run(
                    [
                        pdftoppm, "-png", "-r", str(dpi),
                        "-f", str(page), "-l", str(page),
                        "-singlefile", str(source), str(prefix),
                    ],
                    capture_output=True,
                    text=True,
                )
                produced = prefix.with_suffix(".png")
                if raster.returncode != 0 or not produced.is_file():
                    report["failed"].append(
                        {"page": page, "reason": raster.stderr.strip() or "pdftoppm produced no page"}
                    )
                    continue
                size = image_dimensions(produced)
                if size is None:
                    report["failed"].append({"page": page, "reason": "rendered page has an unreadable header"})
                    produced.unlink()
                    continue
                width, height = size
                if max(width, height) > args.max_edge:
                    # The DPI ceiling should prevent this; never hand the harness a page
                    # it will re-encode into a large PNG.
                    width, height = resize_targets(width, height, args.max_edge)
                target = output_dir / f"page-{page:03d}{DELIVERED_EXTENSION}"
                handle, temporary_name = tempfile.mkstemp(dir=str(output_dir), suffix=DELIVERED_EXTENSION)
                os.close(handle)
                temporary = Path(temporary_name)
                try:
                    encode_page(
                        cwebp, produced, temporary, args.quality,
                        resize_arguments(width, height, args.max_edge),
                    )
                    if target.is_file():
                        if temporary.read_bytes() == target.read_bytes():
                            report["skipped"].append(
                                {"page": page, "reason": "already rendered with identical bytes"}
                            )
                            continue
                        report["failed"].append(
                            {"page": page, "reason": f"{target.name} already exists with different bytes"}
                        )
                        continue
                    os.replace(temporary, target)
                except RenderError as error:
                    report["failed"].append({"page": page, "reason": str(error)})
                    continue
                finally:
                    if produced.exists():
                        produced.unlink()
                    if temporary.exists():
                        temporary.unlink()
                delivered = image_dimensions(target)
                if delivered is None or max(delivered) > args.max_edge:
                    report["failed"].append(
                        {"page": page, "reason": f"delivered page is outside the {args.max_edge}px ceiling"}
                    )
                    target.unlink(missing_ok=True)
                    continue
                encoded = target.stat().st_size
                report["rendered"].append(
                    {
                        "page": page,
                        "file": target.name,
                        "dimensions": list(delivered),
                        "bytes": encoded,
                        "base64_bytes": base64_size(encoded),
                    }
                )
                report["bytes"] += encoded
                report["base64_bytes"] += base64_size(encoded)

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 1 if report["failed"] else 0


def resize_targets(width: int, height: int, max_edge: int) -> tuple[int, int]:
    if width >= height:
        return max_edge, max(1, round(height * max_edge / width))
    return max(1, round(width * max_edge / height)), max_edge


if __name__ == "__main__":
    sys.exit(main())
