Use `$slide-layout-refiner` with a multimodal model. Preferred model: `MiniMax-M3`.

Inputs:

- original PDF: `<absolute-source-pdf-outside-vault>`
- base Markdown: `<absolute-base-markdown-staging-path>`
- assets directory: `<absolute-assets-path>`
- candidate Markdown: `<absolute-candidate-staging-path>`

Read the original PDF visually, page by page, together with the matching `<!-- source-page: N -->` segment in the base Markdown.

Treat every source-page marker as a locked separator. Edit one slide segment at a time and never move text or assets across the previous/next marker.

Correct layout only:

- identify real slide-title/section/body hierarchy;
- demote fragmented pseudo-headings;
- normalize decorative bullet glyphs into lists;
- allocate at most one true H2 slide title, then H3 regions and H4 nested labels;
- restore paragraph, nested/ordered list, table, blockquote, emphasis, highlight, and embed structure suggested by the slide;
- reposition or resize existing asset embeds within the same page.

Do not change, correct, add, omit, translate, summarize, or reorder visible content. Do not move an asset across page markers or invent captions. Do not use callouts, raw HTML/CSS, Mermaid, or plugin-specific layout syntax. Preserve frontmatter and page markers byte-for-byte. Write only the candidate file; never overwrite the base or final note.

After writing, return the candidate path for deterministic validation.
