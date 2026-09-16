# MinerU output normalization (optional aid)

**This document applies only to `--extraction mineru`.** When the model reads the source natively, there is no MinerU output to normalize and no page marker to place; content coverage is recorded in `page-ledger.json` instead.

Canonical output documentation: <https://opendatalab.github.io/MinerU/reference/output_files/>

Use structured MinerU output as the source of page identity and block type. `full.md` is a rendering aid, not a reliable page-index database.

## Preferred page source

1. Use the page-group JSON produced by `mineru-cli-adapter.py`.
2. The adapter groups legacy blocks by integer `page_idx` and preserves block order within each page.
3. Never locate pages with a global Markdown string anchor.

Overview pages and detail pages often repeat text. Page grouping prevents a repeated item from resolving to the earlier summary occurrence.

## Page-count source of truth

Set the plan and ledger `source_pages` from the structured MinerU result, usually `len(normalized_page_groups)`. Spotlight metadata, `file` output, and PDF metadata are diagnostic only. Record every observed count in the temporary QA report.

## Two consumers

- **Content-driven notes.** `plan-note-structure.py` reads the page groups to propose section headings from the document's own outline and to emit a draft page ledger with furniture pages already classified. Per-page text recall is then available during validation, which is strictly stronger than the evidence-only check used for pure native reading.
- **Faithful transcription.** `reconstruct-note.py` renders Markdown with `<!-- source-page: N -->` markers for `policy-document` and `paper`. The marker is 1-based and goes immediately before the first included block from that page. MinerU `page_idx` is 0-based.

## Headings

- Legacy content: use `text_level`; no value or `0` is body, `1` is H1-level source text, `2` is the next level.
- V2 content: use `title` blocks and `content.level`.
- Do not apply global regex demotion before reconstruction; compare adjacent blocks, numbering, bbox/style evidence, and profile semantics.
- Preserve explicit source numbering by default.

For content-driven notes, MinerU heading levels are *evidence*, never the outline. The outline is the document's own section structure, which you confirm by reading the source.

## Auxiliary blocks

Inventory legacy `header`, `footer`, `page_number`, `aside_text`, and `page_footnote`, plus V2 `page_header`, `page_footer`, `page_number`, `page_aside_text`, and `page_footnote`.

- Omit repeated navigation chrome and recurring headers/footers only when they are not substantive.
- Preserve a header/footer when it carries document meaning.
- Record every omitted auxiliary type and affected page in the report.
- Do not infer that absence from `full.md` means the block did not exist; check the content list.

## Visual inventory and fallbacks

Count image/chart, table, equation, and fallback-page artifacts, and report zeros explicitly. A zero-asset result is valid only when the report says the source contained zero retained visual blocks and no fallback was generated.

## Structural vs visual verification

Structural alignment uses page-grouped content lists, layout metadata, block counts, page order, headings, auxiliary blocks, and asset references. Pixel-level visual comparison requires rendering the source pages and is outside this composition skill unless a separate renderer is explicitly available. Mark it `NOT-CHECKED`, never `PASS`, when it was not performed.
