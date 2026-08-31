# Output contract

The source original remains outside the Obsidian vault. The default deliverable is one self-contained derived folder per document:

```text
<vault_root>/
└── <course-folder>/
    └── Lectures/
        └── <document-slug>/
            ├── <document-slug>.md
            ├── <document-slug>.canvas
            ├── assets/
            │   ├── page-003-figure-01.png
            │   └── page-007-fallback.png
            └── conversion-report.md
```

The folder must not contain PDF, PPT/PPTX, DOC/DOCX, XLS/XLSX, or archive originals. It must not depend on staging paths.

## Complete Markdown

The Markdown file is the complete course material, not a summary. It contains:

1. YAML properties with supported source metadata and conversion profile.
2. Exactly one H1 title.
3. All substantive content in page/block reading order.
4. Page markers immediately before the first included text/title block from each page.
5. Relative Obsidian embeds for extracted images, tables, equations, or fallback pages.
6. Explicit uncertainty markers only where review is required.
7. Profile-specific additions such as `## In-class notes` only when appropriate.

Required top-level properties:

```yaml
type: course-material
course: IS0000
title: Example document
source_filename: example.pdf
source_format: pdf
source_sha256: <sha256>
source_pages: 14
conversion_profile: lecture-notes
mineru_model: vlm
status: pre-class
```

Do not store the absolute source path in the note by default.

## Assets

- Copy only derived MinerU images or explicitly generated visual fallback pages.
- Use deterministic lowercase filenames containing the 1-based source page number.
- Keep assets local to the document folder.
- When there are no figures, tables, equations, or fallback pages, keep `assets/` empty and report all four zero counts explicitly.
- Never place the original document in `assets/`.

## Relationship canvas

Create `<document-slug>.canvas` according to [canvas-contract.md](canvas-contract.md). It links the full Markdown, its headings, extracted assets, key concepts, and evidence-based relationships. It must not link or embed the source original.

## Conversion report

Fill [../templates/conversion-report.md](../templates/conversion-report.md). The report must contain these fixed sections:

- `## Matched routing`
- `## Pipeline`
- `## Outputs`
- `## Content inventory`
- `## Quality gates`
- `## Review items`
- `## Not checked`

Include figures, tables, equations, fallback pages, page headers, page footers, and page footnotes even when counts are zero. Record omitted auxiliary blocks and the conversion profile.

Never include the API token, Authorization header, signed upload URL, result URL, CDN query parameters, raw response headers, or absolute source path. A redacted task/batch reference is allowed for timeout recovery.

## Overwrite and idempotence

Default to no overwrite. Stable input/configuration should produce stable folder and asset names. Never replace user-authored additions without an explicit merge strategy. A filename collision with different source hashes requires a distinct document slug or user decision.
