# Obsidian lecture-note style

Shape the output for pre-class reading and in-class annotation, not as a raw transcript of every text box.

## Properties

Use only metadata supported by the source or user input. A typical note may begin with:

```yaml
---
type: lecture-note
course: IS0000
lecture: 03
source: lecture-03.pdf
status: pre-class
tags:
  - lecture
---
```

Omit unknown fields instead of inventing values.

## Structure

- Use one H1 title and logical H2/H3 sections.
- Preserve source order unless there is clear evidence that layout order differs from reading order.
- Convert repeated visual bullets into Markdown lists.
- Keep concise slide labels when they help navigation; remove decorative repetition only when meaning is unaffected.
- Leave useful whitespace or an `## In-class notes` section where the user can add notes.

## Obsidian syntax

- Use standard relative Markdown links by default for portability.
- Use Obsidian embeds only when the destination vault conventions call for them.
- Use callouts for conversion warnings, not for every ordinary note.
- Keep equations in valid LaTeX delimiters when the source is reliable; otherwise preserve a fallback image and flag the uncertainty.
- Use Markdown tables only when row and column relationships are unambiguous.

## Visual fallback

Embed or link a page image near the corresponding content when the page contains a diagram, spatial comparison, annotated screenshot, or complex table that would lose meaning as linear text.
