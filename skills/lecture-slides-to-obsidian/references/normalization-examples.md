# MinerU normalization examples

These page-group examples apply to `--extraction mineru`. For the default native path, the equivalent decision is made by the model while reading the page, and the outcome is recorded in the page ledger.

## Content-driven note (plan input)

MinerU page groups feed `scripts/plan-note-structure.py --page-groups`, which proposes sections from the document's own outline:

```json
[
  [{"type":"title","content":{"title_content":[{"type":"text","content":"Week 3 Qualitative Research"}],"level":1}}],
  [{"type":"paragraph","content":{"paragraph_content":[{"type":"text","content":"1. Grounded theory\n2. Action research\n3. Ethnography"}]}}],
  [{"type":"title","content":{"title_content":[{"type":"text","content":"1. Grounded theory"}],"level":2}},
   {"type":"paragraph","content":{"paragraph_content":[{"type":"text","content":"Coding stages and saturation."}]}}]
]
```

Proposed plan: three sections with the numbered outline as headings, page 1 classified as `title-slide`, and one ledger row per page. The Agent still reads the source and corrects the proposal before setting `draft: false`.

## Faithful transcription

Normalized page-group input for `reconstruct-note.py`:

```json
[
  {"type":"title","content":{"title_content":[{"type":"text","content":"Learning objectives"}],"level":1}},
  {"type":"list","content":{"list_items":["Explain X","Compare Y"]}}
]
```

Output:

```markdown
<!-- source-page: 1 -->

## Learning objectives

- Explain X
- Compare Y
```

## Policy document

Input where MinerU labels every title as level 2 and misses one short item:

```json
[
  {"type":"title","content":{"title_content":[{"type":"text","content":"Overview"}],"level":2}},
  {"type":"paragraph","content":{"paragraph_content":[{"type":"text","content":"1. Do not plagiarize."}]}},
  {"type":"title","content":{"title_content":[{"type":"text","content":"Category One"}],"level":2}},
  {"type":"paragraph","content":{"paragraph_content":[{"type":"text","content":"1. Do not plagiarize."}]}}
]
```

Output:

```markdown
## Overview

**1. Do not plagiarize.**

## Category One

### 1. Do not plagiarize.
```

The `current_h2` state distinguishes an overview list from detailed numbered rules. Preserve numbering.

## Paper

Map source title levels relative to the single note H1:

```text
MinerU level 1 title -> Markdown H2
MinerU level 2 title -> Markdown H3
body paragraph       -> paragraph
equation_interline   -> display math
```

## Duplicate anchors

If the same sentence appears in an overview and a detail page, use the page group rather than searching Markdown globally. Page markers are inserted from the outer-array index, so identical text can appear on separate pages without collision.

## Body font in this repository

These examples use ASCII only; the repository validator rejects machine-specific absolute paths in committed examples.
