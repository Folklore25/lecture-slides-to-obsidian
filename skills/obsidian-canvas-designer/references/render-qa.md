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

The machine-readable profile is [../config/render-profile.mbp14-composer.json](../config/render-profile.mbp14-composer.json). `canvas-render-qa.py` fails closed if version, screen, theme, font, line height, or pixel ratio differs. Do not guess substitute parameters and do not claim cross-machine compatibility.

## Measured height formula

For each rendered text node, the script finds every real child of `.markdown-preview-sizer` except the pusher and measures the largest:

```text
child.offsetTop + child.offsetHeight + child.marginBottom
```

The local renderer needs `34px` beyond that bottom: `16px` top inset, `16px` bottom inset, and `2px` node border. Add another `8px` safety margin and round up to `10px`. The rounded result retains roughly 10–19px actual headroom without the oversized empty tails seen in earlier cards:

```text
exact_required = max_child_bottom + 34
required_height = ceil_to_10(exact_required + 8)
```

The local experiment reproduced the supplied failure:

| Card | Measured bottom | Exact required | Profile height |
|---|---:|---:|---:|
| Legacy long policy card | 525 | 559 | 570 |
| Plagiarism card | 434 | 468 | 480 |
| Public-interest card | 436 | 470 | 480 |

Their previous `440px` height was short by roughly `119px`, `28px`, and `30px` respectively.

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
- The final check's Canvas SHA-256 matches the delivered `.canvas` file.
- Reading zoom is `0`; effective Canvas body text is `16px`, not smaller than the `13px` sidebar reference.
- Screenshots are not part of the default gate. They cost context and introduce model-dependent judgment.
- If the local DOM contract changes or the render profile mismatches, stop and recalibrate instead of falling back to image inspection or the old character-count estimate.
