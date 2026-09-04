# Canvas renderer QA

JSON Canvas stores a fixed `width` and `height` for every node. It does not define auto-height from rendered Markdown. Therefore the offline estimator in `build-canvas.py` is only a first pass; completion requires measurement in the local Obsidian renderer.

Authoritative format reference: <https://jsoncanvas.org/spec/1.0/>. Obsidian CLI provides `open`, `eval`, and DOM developer commands: <https://obsidian.md/help/cli>.

## Supported workstation profile

This repository intentionally supports one measured environment for now:

- MacBook Pro 14-inch logical screen: `1512 × 982` CSS px;
- device pixel ratio: `2`;
- Obsidian: `1.13.7` with installer `1.12.4`;
- theme: `Composer`;
- base font size: `16`;
- rendered Canvas Markdown: `16px` font, `27.2px` line height;
- file-navigation/sidebar text: `13px`.

The machine-readable profile is [../config/render-profile.mbp14-composer.json](../config/render-profile.mbp14-composer.json). `canvas-render-qa.py` fails closed if version, screen, theme, font, line height, pixel ratio, or compactness thresholds differ. Do not guess substitute parameters and do not claim cross-machine compatibility.

## Measured height formula

For each rendered text node, the script finds every real child of `.markdown-preview-sizer` except the pusher and measures the largest:

```text
child.offsetTop + child.offsetHeight + child.marginBottom
```

The local renderer needs `34px` beyond that bottom: `16px` top inset, `16px` bottom inset, and `2px` node border. Add an `8px` safety margin and round up to the profile's `4px` grid. The supported profile accepts only `8–12px` of effective headroom after this chrome; a card with more is too loose and fails final renderer QA. This normally produces roughly 8–10px without the oversized empty tails seen in earlier cards:

```text
exact_required = max_child_bottom + 34
required_height = ceil_to_4(exact_required + 8)
```

The compactness gate is two-sided:

```text
8px <= node.height - (max_child_bottom + 34px) <= 12px
```

The lower bound prevents clipping. The upper bound prevents stale or overly generous geometry from passing merely because the text fits. When the upper bound fails, rebuild from the same DOM measurements; do not manually hide the extra space with zoom.

The local experiment reproduced the supplied failure:

| Card | Measured bottom | Exact required | Profile height |
|---|---:|---:|---:|
| Legacy long policy card | 525 | 559 | 570 |
| Plagiarism card | 434 | 468 | 480 |
| Public-interest card | 436 | 470 | 480 |

Their previous `440px` height was short by roughly `119px`, `28px`, and `30px` respectively.

## Top-lane reflow

The Composer renderer places a learning-module group label roughly `58` canvas px above the group's stored `y`. A nominal 50 px gap between the overview and group bounds therefore still allows the label to overlap the overview. The supported profile requires:

```text
top_lane_bottom = max(overview_bottom, source_preview_bottom)
module_group_y = ceil_to_10(top_lane_bottom + 80)
```

The extra 80 px contains the upward-rendered label and leaves about 20 px of visible separation without creating a large empty band. `build-canvas.py` must recompute this value from DOM-measured overview height during the second pass. `canvas-aesthetic-qa.py` and final renderer `check` both fail when clearance is below 80 px.

## Font-size/readability formula

Canvas zoom scales text and cards together:

```text
effective_font_px = 16 × 2^canvas_zoom
```

The local sidebar text is `13px`, so body-text reading requires:

```text
canvas_zoom >= log2(13 / 16) ≈ -0.30
```

The supported reading viewport is `zoom = 0` (`1:1`), producing an effective `16px` Canvas font. `Zoom to fit` (`Shift+1`) may shrink a large map far below `13px`; it is useful only for orientation and must never be used to claim that card text is readable. Final renderer QA leaves the viewport centered on the overview at `zoom = 0`.

## Mandatory two-pass workflow

Obsidian must be running with its CLI enabled.

The script brings Obsidian to the foreground on the supported Mac before measuring. A mounted node with no rendered Markdown children or zero content height is a hard failure; never treat it as an empty 50px card.

1. Build the first Canvas normally.
2. Measure actual DOM layout:

```text
scripts/canvas-render-qa.py measure \
  --canvas <document.canvas> \
  --vault-root <vault-root> \
  --output <staging>/canvas-render-metrics.json
```

3. Rebuild and reflow with the measured heights:

```text
scripts/build-canvas.py \
  --note <document.md> \
  --vault-root <vault-root> \
  --profile <conversion-profile> \
  --model <staging>/recall-model.json \
  --render-metrics <staging>/canvas-render-metrics.json \
  --output <document.canvas> \
  --overwrite
```

4. Verify the delivered file in Obsidian:

```text
scripts/canvas-render-qa.py check \
  --canvas <document.canvas> \
  --vault-root <vault-root> \
  --output <staging>/canvas-render-check.json
```

5. For standalone Canvas-only work, retain or clean the QA files according to the user's request after reporting PASS. For delegated work, return both files plus the final aesthetic check to the parent skill; its package validator owns final cleanup.

## Acceptance rules

- Every text node is mounted and rendered in Obsidian; no source-text estimate counts as final evidence.
- `node.height >= required_height` for every text node. Merely reaching the exact unclipped height is insufficient; retain the measured `8px` margin before grid rounding.
- `8px <= headroom <= 12px` for every text node. A large empty tail is a readability/scanability failure, not a cosmetic preference.
- The learning-module group row begins at least `80px` below the bottom of the overview/source lane after the measured rebuild.
- The final check's Canvas SHA-256 matches the delivered `.canvas` file.
- Reading zoom is `0`; effective Canvas body text is `16px`, not smaller than the `13px` sidebar reference.
- Screenshots are not part of the default gate. They cost context and introduce model-dependent judgment.
- If the local DOM contract changes or the render profile mismatches, stop and recalibrate instead of falling back to image inspection or the old character-count estimate.
