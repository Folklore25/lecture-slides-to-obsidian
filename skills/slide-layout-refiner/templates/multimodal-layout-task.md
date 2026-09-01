Use `$slide-layout-refiner` with a multimodal model. Preferred model: `MiniMax-M3`.

Inputs:

- original PDF: `<absolute-source-pdf-outside-vault>`
- target Markdown: `<absolute-final-markdown-path-in-vault>`
- assets directory: `<absolute-assets-path>`

Read the original PDF visually, page by page, together with the matching `<!-- source-page: N -->` segment in the target Markdown.

Treat every source-page marker as a locked separator. Edit one slide segment at a time and never move text or assets across the previous/next marker.

Correct layout only:

- identify real slide-title/section/body hierarchy;
- demote fragmented pseudo-headings;
- normalize decorative bullet glyphs and line-leading `\-` into real `-` list items;
- when the source expresses a parent/detail hierarchy, place children directly below the parent and use exactly four ASCII spaces per nesting level before `- `; never use Tab indentation;
- allocate at most one true H2 slide title, then H3 regions and H4 nested labels;
- restore paragraph, nested/ordered list, table, blockquote, emphasis, highlight, and embed structure suggested by the slide;
- reposition or resize existing asset embeds within the same page.

Do not change, correct, add, omit, translate, summarize, or reorder visible content. Do not move an asset across page markers or invent captions. Do not use callouts, raw HTML/CSS, Mermaid, or plugin-specific layout syntax. Preserve frontmatter and page markers byte-for-byte.

Optimize for complete information preservation and reading clarity, not pixel-perfect slide reconstruction. Overwrite the target Markdown directly. Do not create a second Markdown file, backup, report, dot-prefixed file, or dot-prefixed directory in the vault. After writing, return the unchanged target path for deterministic validation.
