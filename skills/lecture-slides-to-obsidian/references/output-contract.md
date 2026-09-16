# Output contract

The source original stays outside the Obsidian vault. The deliverable is one self-contained derived folder per document.

```text
<vault_root>/
└── <course-folder>/
    └── Lectures/
        └── <document-slug>/
            ├── <note-slug>.md          # one or more
            ├── <note-slug>.canvas      # exactly one per note
            └── assets/
                ├── qualitative-research-cycle.png
                └── coding-stages.png
```

The folder must not contain a conversion report, PDF, PPT/PPTX, DOC/DOCX, XLS/XLSX, archive original, second/backup note, or dot-prefixed file/directory. It must not depend on staging paths.

## Notes

Each note is a complete, readable knowledge artifact:

1. Minimal YAML properties (see below). No page-provenance fields.
2. Exactly one H1 whose text is the note title.
3. H2 headings that equal the planned section headings from `note-plan.json`.
4. Real Markdown prose, lists, and tables for substantive content.
5. Relative Obsidian embeds for the visuals that survived selection.
6. Explicit uncertainty markers only where review is required.
7. `## In-class notes` last, for `lecture-notes` only.

A note produced by native reading must not contain `<!-- source-page: N -->` markers. Markers are part of the MinerU faithful-transcription contract only, and page coverage is carried by `page-ledger.json` instead.

Every `## H2` is a Canvas anchor: keep headings stable, unique inside a note, and free of page furniture.

Required properties:

```yaml
---
type: course-material
course: COURSE101
title: Example document
source_filename: example.pdf
source_format: pdf
source_sha256: <sha256>
conversion_profile: lecture-notes
mineru_model: native
status: pre-class
---
```

`mineru_model` records `native` or the CLI model (`vlm`, `pipeline`). Do not store the absolute source path in the note.

## Assets

- Copy only derived visuals: extracted figures or self-produced crops that carry meaning.
- Follow [asset-naming.md](asset-naming.md): lowercase semantic kebab-case, for example `coding-stages.png`.
- Keep assets flat under the document's `assets/`, and reference every asset from a note embed or a Canvas file node.
- Never place the original document in `assets/`.
- `page-PPP-kind-NN.ext` remains valid only for `--extraction mineru` transcription folders.

## Note plan and page ledger

Both are temporary Agent QA state under staging, outside the vault. `scripts/plan-note-structure.py` drafts them; the Agent corrects them against the source it actually read.

`note-plan.json`

```json
{
  "schema_version": 1,
  "profile": "lecture-notes",
  "granularity": "single-note",
  "source_pages": 44,
  "draft": false,
  "notes": [
    {
      "slug": "l03-week3",
      "title": "Week 3 Qualitative Research",
      "sections": [
        {"heading": "1. Research methodology", "pages": [2, 3, 4], "subtopics": ["Method versus technique"]}
      ]
    }
  ]
}
```

`page-ledger.json`

```json
{
  "schema_version": 1,
  "draft": false,
  "source_pages": 44,
  "pages": [
    {"page": 1, "disposition": "dropped", "reason": "title-slide"},
    {
      "page": 3,
      "disposition": "merged",
      "note": "l03-week3",
      "section": "1. Research methodology",
      "evidence": "An interview is a data collection technique, not a method",
      "visuals": [
        {"disposition": "kept", "asset": "qualitative-research-cycle.png"},
        {"disposition": "dropped", "reason": "superseded-by-table", "rendered_as": "markdown-table"}
      ]
    }
  ]
}
```

Rules:

- Every source page appears exactly once.
- `disposition` is `kept`, `merged`, or `dropped`.
- `dropped` requires a reason from: `title-slide`, `section-divider`, `agenda`, `course-admin`, `exercise`, `repeated-chrome`, `page-furniture`, `duplicate`, `illegible`, `non-substantive`.
- Dropping more than half of the source pages needs `--allow-heavy-drop`.
- `kept` and `merged` require `note`, `section`, and an `evidence` phrase that must literally appear in that note.
- When MinerU page groups are available, page-level text recall is checked on top of the evidence phrase. A legitimately distilled page may set `recall_exempt` plus `recall_exempt_reason`; nothing is skipped silently.

### Visuals

**Extracting a visual is the default.** Every kept or merged page declares `visuals`: a list, possibly empty, saying what happened to each visual on that page.

- `{"disposition": "kept", "asset": "<semantic-name>.<ext>"}` — the visual was extracted, named, and embedded at its point of use. The file must exist under `assets/` and be embedded by its note or attached to a Canvas concept.
- `{"disposition": "dropped", "reason": "<reason>"}` — the visual was genuinely not worth keeping. Allowed reasons: `repeated-chrome` (logo, watermark, template ornament, footer bar), `decorative`, `redundant-with-text`, `duplicate`, `illegible`, `superseded-by-table`.

The planner pre-classifies repeated chrome: a visual block whose position and size recur on at least half the pages is marked `repeated-chrome` in the draft ledger, so template furniture is dismissed once rather than page by page. Everything else starts as `kept` with an empty asset name, which cannot validate until you name it or give a reason.
- `superseded-by-table` must also state `"rendered_as": "markdown-table"`, so replacing a visual with text is an explicit, auditable choice rather than a silent omission.

Describing a diagram, chart, matrix, or annotated figure in prose and then dropping it is not allowed. A prose description accompanies a visual; it never replaces one.

The ledger and `assets/` are cross-checked in both directions: every asset must be declared as kept, and every declared asset must exist and be embedded.

## Knowledge-recall Canvas

Delegate `<note-slug>.canvas` to `obsidian-canvas-designer` following its [delegation contract](../../obsidian-canvas-designer/references/delegation-contract.md). It must link every concept back to its note and must not link or embed the source original. The staging recall model, aesthetic check, and both DOM render-QA JSON files are temporary and must not enter the vault.

## Temporary conversion report

Build a context JSON matching [../templates/report-context.example.json](../templates/report-context.example.json), then run `scripts/fill-report.py`. Write the result under staging, outside the Obsidian vault. Fixed sections:

- `## Matched routing`
- `## Pipeline`
- `## Outputs`
- `## Content inventory`
- `## Quality gates`
- `## Review items`
- `## Not checked`

Include figures, tables, equations, fallback pages, page headers, page footers, and page footnotes even when counts are zero. Record the extraction mode, the granularity decision, and the conversion profile.

Never include the API token, Authorization header, signed upload URL, result URL, CDN query parameters, raw response headers, or absolute source path.

Delete the report immediately after successful validation and summary. Preserve it only while debugging a failure.

## Overwrite and idempotence

Default to no overwrite. Stable input and configuration should produce stable folder, note, and asset names. Never replace user-authored additions without an explicit merge strategy. A filename collision with a different source hash requires a distinct document slug or a user decision.
