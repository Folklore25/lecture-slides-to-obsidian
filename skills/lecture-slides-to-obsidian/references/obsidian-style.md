# Obsidian note style

Write a readable knowledge note, not a slide dump and not a summary of the model's own process. Apply the profile from [document-profiles.md](document-profiles.md).

## Anatomy of a content-driven note

```markdown
---
<minimal properties>
---

# Week 3 Qualitative Research

> One or two sentences framing what this material answers.

## 1. Research methodology

Prose that states the idea, then the mechanism, then the boundary.

| Qualitative | Quantitative |
| --- | --- |
| Understand and interpret | Describe, explain, and predict |

## 2. Grounded theory

- **Open coding** labels phenomena.
- **Axial coding** interconnects the categories.

## In-class notes
```

- Exactly one H1: the note title.
- H2 headings equal the planned section headings and act as Canvas anchors.
- H3 and deeper for sub-topics only; never use a heading for a page footer, a logo line, or a page number.
- Prefer short paragraphs, tight lists, and real tables over long undifferentiated bullet runs.
- Preserve explicit source numbering inside headings when the source uses it for cross-reference.
- Do not restate the extraction or your own reasoning. The note is the material.

## Distillation rules

Keep:

- definitions, mechanisms, causal chains, and decision rules;
- formulas and their conditions of use;
- comparison matrices, classifications, and taxonomies;
- worked-example logic and the conclusion it demonstrates;
- stated limits, failure modes, and exceptions;
- cited sources and provenance lines.

Drop:

- welcome, agenda, outline, and section-divider pages;
- course-admin pages (invitation codes, staff contact blocks, schedules);
- exercise, quiz, and answer pages;
- repeated title bars, logos, page numbers, and deck footers;
- decorative stock slides;
- the same summary restated two or three times.

Mark each dropped page in the ledger with a controlled reason.

## Obsidian syntax

- Use `[[wikilinks]]` for internal notes and `![[assets/file.png|420]]` for local embeds.
- Use standard Markdown links only for external URLs.
- Keep equations in LaTeX delimiters so they render in MathJax.
- Use callouts for warnings or review items, not for ordinary source content. Wrap conversion-generated callouts in `<!-- conversion-layer:<kind>:<id>:start -->` / `<!-- conversion-layer:<kind>:<id>:end -->` markers.
- Prefer a Markdown table over an image only for a legible numeric data table. For anything whose structure matters, keep the visual.

## Assets

Extract the visual; do not paraphrase it away. Embed each one next to the idea it explains
(`![[assets/coding-stages.png|420]]`), at the position where it appears in the source's reading flow.

A prose description may accompany a visual, never replace it. If the source genuinely contained no
meaningful visual, create none and report the zero counts.

## Page markers

`<!-- source-page: N -->` appears only in MinerU-mode faithful transcription. Never add markers to a note produced by native reading.
