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

**Extracting the visual is the default.** A diagram, chart, matrix, taxonomy, annotated figure, or
screenshot that carries information the prose does not must be extracted, named, and embedded at the
point in the note where it belongs.

- **Never summarize a visual in prose and drop it.** A textual description is a supplement to the
  image, never a replacement.
- Replace a visual with text only when that text carries exactly the same information — in practice a
  legible numeric data table. Declare it in the page ledger as `superseded-by-table` with
  `rendered_as: "markdown-table"`.
- Place the embed where the visual sits in the source's reading flow, not collected at the end.
- The Canvas cap of six memory-critical visuals applies to the **Canvas only**. It never limits what
  the note itself keeps.

### A crop must contain the thing it is named after

The quietest failure in this pipeline is a crop that misses its subject: a thin strip of table edge still resolves, still gets embedded, and still passes every filename and reference rule while carrying nothing. `validate-output.py` rejects an asset whose shorter side is under `40px` or whose aspect ratio exceeds `8:1`. When that fires, re-crop the page instead of renaming the file — an asset called `what-is-data-table.png` that shows four labels and the edge of a table is worse than no asset, because the note then reads as if the example were present.

### Tables and equations are not visuals

A source table becomes a Markdown table; a source equation becomes LaTeX. Both are text, which is searchable, editable, and checkable, while an image of a formula is none of those. Embedding either as an image is an exception that needs a stated reason in the ledger; the default is transcription.

### Drop without hesitation

Deck furniture and artwork that carries no information. Each one still gets a declared reason in the
page ledger, but none of them belongs in the note.

| What it looks like | Ledger reason |
| --- | --- |
| University crest, faculty wordmark, partner logos, watermarks | `repeated-chrome` |
| Template background, border, ribbon, corner accent, colour bar | `repeated-chrome` |
| Slide-number graphics, footer bars, section-tab strips | `repeated-chrome` |
| Decorative clipart, stock photography, generic icon art | `decorative` |
| A schematic the surrounding text already states in full | `redundant-with-text` |
| The same figure repeated again on a summary slide | `duplicate` |
| Unreadable scan, broken render, placeholder artwork | `illegible` |
| A legible numeric data table replaced by a Markdown table | `superseded-by-table` |

The planner does the tedious part for you: a visual block whose position and size recur on at least
half the pages is almost always template furniture, and the draft ledger already marks it
`repeated-chrome`. Review that draft instead of re-deciding the same logo on every page.

### Keep without hesitation

- process and flow diagrams, feedback loops, state machines;
- taxonomies, classification matrices, decision trees;
- charts and plots that carry data;
- annotated figures, screenshots, and worked examples whose layout matters;
- an equation image whose notation cannot be transcribed reliably.

**If in doubt, keep it.** An extra image costs the reader one glance; a dropped diagram costs them
the idea, and nothing in the note reveals it was ever there.
