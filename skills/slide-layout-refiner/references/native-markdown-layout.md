# Native Markdown slide layout

Use Obsidian-native Markdown structures according to the PDF's actual visual hierarchy. Variety is useful only when it represents structure; do not decorate every slide with every syntax.

## Heading allocation

- The document's existing H1 remains unchanged in the preamble.
- Inside one source-page segment, use at most one H2 for the true visible slide title.
- Use H3 for major internal regions, column headings, or named concepts that are visually subordinate to the slide title.
- Use H4 only for labels nested under an H3 region.
- If a slide has no visible title, do not invent one. It may contain H3 regions without an H2.
- Never place H1 inside a slide, retain several MinerU pseudo-H2 blocks, or jump to H4 without an earlier H3 in the same slide.

## Native structures

- Unordered lists: parallel points.
- Nested lists: visible parent/detail hierarchy such as a `Systematic` point followed by `about research design`.
- Ordered lists: actual sequence, stages, or ranking.
- Tables: true row/column comparison, matrix, label/value grid, or schedule. Preserve left-to-right then top-to-bottom text order.
- Blockquotes: source material visually presented as a quotation; not a generic container.
- Bold, italic, and highlight: only when the PDF visibly emphasizes the same text.
- Obsidian embeds: `![[assets/file.png|width]]`, positioned inside the same slide beside related content.
- Math/code fences: preserve when the source already contains math/code; do not invent them as decoration.

Do not use callouts because their generated titles introduce visible words. Do not use raw HTML, custom CSS, Mermaid, or plugin-specific columns. Source-page comments are the only slide separators.
