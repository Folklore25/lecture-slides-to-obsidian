# MinerU output normalization

Canonical output documentation: <https://opendatalab.github.io/MinerU/reference/output_files/>

Use structured MinerU output as the source of page identity and block type. `full.md` is a rendering aid, not a reliable page-index database.

For concrete before/after cases, read [normalization-examples.md](normalization-examples.md) and use `scripts/reconstruct-note.py` as the reference implementation.

## Preferred page source

1. Use the page-group JSON produced by `mineru-cli-adapter.py` from the official CLI content list.
2. The adapter groups legacy blocks by integer `page_idx` and preserves block order within each page.
3. If a future CLI emits native V2 page groups, prefer them without changing the reconstruction contract.
4. Never locate pages with a global Markdown string anchor.

Overview pages and detail pages often repeat text. Page grouping prevents a repeated item from resolving to the earlier summary occurrence.

## Page-count source of truth

Set `source_pages` from the structured MinerU result:

1. `len(normalized_page_groups)` from the CLI adapter;
2. the adapter derives this as `max(page_idx) + 1` from official CLI JSON;
3. native V2 length if a compatible future CLI exposes it.

Spotlight metadata, `file` output, PDF metadata, and other local estimates are diagnostic only. When they disagree, keep the structured MinerU count and record every observed count/source in the temporary QA report. Do not ask the Agent to choose ad hoc.

## Page marker semantics

MinerU `page_idx` is 0-based; `<!-- source-page: N -->` is 1-based.

Place each marker immediately before the first included text/title/content block from source page N. The first non-empty note line after the marker must derive from that page. If a paragraph crosses a page boundary, do not split or duplicate it without block evidence; record the ambiguity.

If `full.md` must be reconciled with structured blocks, search only inside a monotonic page window bounded by the previous and next page's verified blocks. Multiple matches require block order and page evidence; never choose the first global occurrence.

## Headings

- Legacy content: use `text_level`; no value or `0` is body, `1` is H1-level source text, `2` is the next level, and so on.
- V2 content: use `title` blocks and `content.level`.
- Normalize into exactly one note H1, then map source levels relative to it.
- Do not apply global regex demotion before page reconstruction.
- If a numbered series has inconsistent MinerU levels, compare adjacent blocks, numbering, bbox/style evidence, and profile semantics. Normalize the series consistently and record the correction.
- Preserve explicit source numbering by default.

## Auxiliary blocks

Inventory legacy `header`, `footer`, `page_number`, `aside_text`, and `page_footnote`, plus V2 `page_header`, `page_footer`, `page_number`, `page_aside_text`, and `page_footnote`.

- Omit repeated navigation/chrome and recurring headers/footers only when they are not substantive.
- Preserve a header/footer when it carries document meaning.
- Record every omitted auxiliary type and affected page in the report.
- Do not infer that absence from `full.md` means the block did not exist; check the content list.

## Visual inventory and fallbacks

Count image/chart, table, equation, and fallback-page artifacts from structured blocks and generated assets. Report zeros explicitly. A zero-asset result is valid only when the report says the source contained zero retained visual blocks and no fallback was generated.

## Structural vs visual verification

Structural alignment uses page-grouped content lists, layout/middle metadata, block counts, page order, headings, auxiliary blocks, and asset references. Pixel-level visual comparison requires rendering the source pages and is outside this composition skill unless a separate renderer is explicitly available. Mark it `NOT-CHECKED`, never `PASS`, when it was not performed.
