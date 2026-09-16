# Asset naming contract

## Content-driven notes (default)

```text
<semantic-slug>.<ext>
```

- Lowercase kebab-case `[a-z0-9]+(-[a-z0-9]+)*`, 3–48 characters.
- The slug names the *idea*, not the page: `coding-stages.png`, `qualitative-research-cycle.png`, `case-study-vs-ethnography.png`.
- One extension from `png`, `jpg`, `jpeg`, `webp`, `gif`, `bmp`, `svg`.
- Flat files directly under the document's `assets/` directory.
- Never use a `page-` prefix, a MinerU hash, a random id, or the original asset basename.
- Never derive a name from a caption sentence; derive it from what the visual explains.

Every asset must be referenced by a note embed (`![[assets/coding-stages.png|420]]`) or a Canvas file node. Unreferenced assets are a validation failure: they are the visible symptom of copying an extraction package instead of choosing a visual.

## MinerU transcription folders

Only for `--extraction mineru` transcription output, keep the deterministic form:

```text
page-<PPP>-<kind>-<NN>.<ext>
```

- `PPP`: 1-based source page, zero-padded to three digits.
- `kind`: `figure`, `table`, `equation`, `chart`, or `fallback`.
- `NN`: sequence within the same page and kind, starting at `01`.

Examples: `page-001-figure-01.png`, `page-004-table-01.png`, `page-012-fallback-01.png`.

Assign names in content-list order so a repeat conversion produces identical names. If one original asset path is referenced repeatedly, copy it once and reuse the first standardized name. A different source file resolving to an occupied name is an error, not an overwrite. `asset-map.json` stays in staging QA and is not copied into the vault.

## Choosing what to keep

- Convert comparison matrices, classifications, and taxonomies into Markdown tables instead of images.
- Keep an image only when the visual carries structure that prose cannot: process diagrams with feedback loops, geometric intuition, annotated screenshots, or a worked figure whose layout matters.
- The Canvas may attach at most six memory-critical visuals.
