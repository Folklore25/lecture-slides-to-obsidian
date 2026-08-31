# Obsidian document style

Create a complete, editable course document, not a summary. Apply the selected profile from [document-profiles.md](document-profiles.md).

## Properties

Use the required properties from [output-contract.md](output-contract.md). A typical note begins:

```yaml
---
type: course-material
course: COURSE101
title: Example Lecture
source_filename: example-lecture.pdf
source_format: pdf
source_sha256: <sha256>
source_pages: 14
conversion_profile: lecture-notes
mineru_model: vlm
status: pre-class
tags:
  - lecture
---
```

Omit unsupported optional metadata instead of inventing it. Do not include the absolute source path or API secrets.

## Structure

- Use exactly one H1 title and logical H2/H3 sections.
- Preserve complete substantive content and structured page order.
- Place `<!-- source-page: N -->` immediately before page N's first included block.
- Preserve source numbering in headings unless the user asks to remove it.
- Do not use one regex to demote all headings; use MinerU structured levels plus series/context consistency.
- Add `## In-class notes` only for `lecture-notes`, unless explicitly requested for another profile.

## Obsidian syntax

- Use `[[wikilinks]]` for internal notes and `![[assets/file.png]]` for local asset embeds.
- Use standard Markdown links only for external URLs.
- Use callouts for conversion warnings and review items, not ordinary source content.
- Keep reliable equations in LaTeX delimiters; otherwise embed the extracted/fallback asset and flag uncertainty.
- Use Markdown tables only when relationships are unambiguous; otherwise preserve the table image and structured HTML/Markdown in a callout or adjacent section.

## Auxiliary blocks

Handle page headers, footers, page numbers, aside text, and footnotes according to [mineru-normalization.md](mineru-normalization.md). Repeated decorative blocks may be omitted only with temporary QA evidence.

## Assets and zero counts

Embed derived visual assets near the corresponding source content. If the source yields zero figures, tables, equations, and fallback pages, create no fake assets; the temporary QA context must state all four zero counts before it is deleted.
