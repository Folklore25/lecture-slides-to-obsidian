# Normalization examples

Use these page-group examples with `scripts/reconstruct-note.py`; they illustrate decisions that raw MinerU levels alone cannot make.

## Lecture notes

Normalized page-group input:

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

Add `## In-class notes` only after all source pages.

## Policy document

Normalized page-group input where MinerU labels every title as level 2 and misses one short item:

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

Do not apply policy short-item promotion to a paper.

## Duplicate anchors

If the same sentence appears in an overview and a detail page, use the adapter's page group. Do not search Markdown globally. Page markers are inserted from the outer-array index, so identical text can appear on separate pages without collision.
