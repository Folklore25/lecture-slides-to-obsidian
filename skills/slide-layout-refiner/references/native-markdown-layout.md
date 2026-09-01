# Native Markdown slide layout

Use Obsidian-native Markdown structures to preserve all information and make the note easier to read. The goal is not pixel-perfect reconstruction of the slide. Use the PDF to recover hierarchy and relationships, then choose the clearest portable Markdown representation. Variety is useful only when it represents structure; do not decorate every slide with every syntax.

## Heading allocation

- The document's existing H1 remains unchanged in the preamble.
- Inside one source-page segment, use at most one H2 for the true visible slide title.
- Use H3 for major internal regions, column headings, or named concepts that are visually subordinate to the slide title.
- Use H4 only for labels nested under an H3 region.
- If a slide has no visible title, do not invent one. It may contain H3 regions without an H2.
- Never place H1 inside a slide, retain several MinerU pseudo-H2 blocks, or jump to H4 without an earlier H3 in the same slide.

## Native structures

- Unordered lists: parallel points. Convert MinerU lines beginning with escaped `\-` or decorative glyphs into real `-` list items.
- Nested lists: parent/detail hierarchy such as `Focus` followed by two specific abilities. Put each child directly under a parent list item and indent each nesting level with exactly four ASCII spaces, followed by `- `; never insert a Tab character. An indented bullet without a parent list item is invalid for this workflow because Obsidian may render it as a code block.

```markdown
- Focus:
    - your understanding of the concepts learned
    - your ability to apply them
```
- Ordered lists: actual sequence, stages, or ranking.
- Tables: true row/column comparison, matrix, label/value grid, or schedule. Preserve left-to-right then top-to-bottom text order.
- Blockquotes: source material visually presented as a quotation; not a generic container.
- Bold, italic, and highlight: only when the PDF visibly emphasizes the same text.
- Obsidian embeds: `![[assets/file.png|width]]`, positioned inside the same slide beside related content.
- Math/code fences: preserve when the source already contains math/code; do not invent them as decoration.

Do not use callouts because their generated titles introduce visible words. Do not use raw HTML, custom CSS, Mermaid, or plugin-specific columns. Source-page comments are the only slide separators.

When visual fidelity conflicts with readability, preserve every piece of information and its order, then choose the clearer native Markdown structure. Do not preserve awkward MinerU escaping or pseudo-layout merely because it resembles the extraction output.
