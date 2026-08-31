# Asset naming contract

All visual files that enter the final document `assets/` directory use:

```text
page-<PPP>-<kind>-<NN>.<ext>
```

- `PPP`: 1-based source page, zero-padded to three digits.
- `kind`: `figure`, `table`, `equation`, `chart`, or `fallback`.
- `NN`: sequence within the same page and kind, starting at `01`.
- `ext`: lowercase original image extension.

Examples:

```text
page-001-figure-01.png
page-001-figure-02.jpg
page-004-table-01.png
page-007-equation-01.png
page-010-chart-01.webp
page-012-fallback-01.png
```

## Type mapping

- MinerU `image` → `figure` unless its subtype is `chart`.
- MinerU `chart` → `chart`.
- MinerU `table` screenshot → `table`.
- MinerU equation screenshot → `equation`.
- Generated full-page visual fallback → `fallback`.
- Seals and other generic visual blocks use `figure` unless a supported kind is explicit.

## Determinism

Assign names in content-list order. Repeating the same conversion with the same structured blocks must produce the same names. Do not derive final names from captions, user text, random IDs, MinerU hashes, or original asset basenames.

If one original asset path is referenced repeatedly, copy it once and reuse its first standardized name. A different source file resolving to an occupied standardized name is an error, not an overwrite.

## Folder and references

- Final visual assets are flat files directly under the document's `assets/` directory.
- Update normalized block paths before Markdown reconstruction.
- Markdown uses `![[assets/page-004-figure-01.png]]`.
- Canvas file nodes use the complete vault-relative path ending in the same filename.
- `asset-map.json` remains in staging QA and records original path, page, kind, index, and final name; it is not copied into the vault.

`scripts/mineru-cli-adapter.py` enforces naming for MinerU-referenced visuals. Any later fallback generator must follow the same function and sequence rules.
