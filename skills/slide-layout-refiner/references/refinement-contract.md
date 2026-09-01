# Content-preserving slide refinement contract

The original PDF is visual evidence for hierarchy and placement. The pre-edit MinerU-derived Markdown snapshot remains the content authority. The overwritten target may change Markdown syntax and page-local asset placement, but not visible content.

There is one Markdown output path. The model edits that target in place. A byte-exact `before.md` snapshot exists only for validation and rollback under the system temporary directory or the installed skill directory. Neither the snapshot nor the validation report may be placed anywhere inside the Obsidian vault.

## Page boundary

`<!-- source-page: N -->` markers are immutable separator lines. The exact marker-line bytes, sequence, numbering, and page count must match. Every transformation occurs inside the closed segment after marker N and before marker N+1. Blank lines inside that segment may change; content cannot cross either marker.

## Visible-text conservation

After removing Markdown-only syntax, the snapshot and overwritten target must produce the same visible token sequence on every page. This allows heading demotion, bullet normalization, line joining, blockquotes, and table separators while rejecting edits, additions, deletions, and reordering.

The validator intentionally treats line-leading escaped `\-` and `▶`, `►`, `▪`, `•`, `●`, `◦`, and `‣` as bullet syntax in the snapshot. The overwritten target must replace them with real Markdown `-` list items. A child item uses exactly four ASCII spaces per nesting level before `- `, must belong to a preceding parent list item, and must never use a Tab character.

## Asset conservation

- Compare exact embed targets per page as a multiset.
- Display-width changes such as `![[asset.png|480]]` are allowed.
- Repositioning within the same page is allowed.
- Cross-page movement, addition, deletion, renamed targets, external images, and invented captions fail.

## Link and metadata conservation

- Frontmatter bytes must be identical.
- Ordinary wikilink and Markdown-link destinations must be unchanged per page.
- Source page comments remain unchanged.
- No `lecture-layer:` markers may exist in either input.

## Existing Callouts

- Compare Callout header lines per page in order. The exact header, including type, fold state, and visible title, must remain unchanged.
- A Callout that already exists in the snapshot is allowed. Do not classify it as user-authored without explicit provenance.
- Adding, removing, retitling, changing the type/fold state of, or reordering a Callout fails validation.
- `lecture-layer:` remains the authoritative stop marker for classroom additions. Conversion-generated fallback Callouts should use `conversion-layer:` markers, which do not trigger the stop rule and must remain byte-identical and in order during refinement.

## Rollback and temporary-path boundary

- Validation failure restores the target from the snapshot automatically and byte-for-byte.
- Rollback is part of the already-authorized overwrite operation; do not interrupt the workflow for another confirmation.
- The vault receives no second Markdown version, backup file, report, hidden directory, or hidden temporary file.
- Delete the snapshot after either successful validation or completed rollback. Delete the report after its result has been consumed.

## Typical corrections

- one slide title remains H2 while labels from a web screenshot become H3/list items;
- a sequence of `▶` lines becomes one Markdown list;
- MinerU output such as `\- detail` becomes `- detail`, or `    - detail` when it belongs under a parent point;
- a diagram embed moves next to its related bullet instead of appearing as an isolated raw asset line;
- visually paired label/value blocks become a Markdown table without changing cell text order.

Exact visual reconstruction is impossible in portable Markdown. Prefer the native structures in [native-markdown-layout.md](native-markdown-layout.md) over custom CSS or new visible labels.
