# Content-preserving slide refinement contract

The original PDF is visual evidence for hierarchy and placement. The MinerU-derived Markdown remains the content authority. The candidate may change Markdown syntax and page-local asset placement, but not visible content.

## Page boundary

`<!-- source-page: N -->` markers are immutable separator lines. The exact marker-line bytes, sequence, numbering, and page count must match. Every transformation occurs inside the closed segment after marker N and before marker N+1. Blank lines inside that segment may change; content cannot cross either marker.

## Visible-text conservation

After removing Markdown-only syntax, base and candidate must produce the same visible token sequence on every page. This allows heading demotion, bullet normalization, line joining, blockquotes, and table separators while rejecting edits, additions, deletions, and reordering.

The validator intentionally treats `▶`, `►`, `▪`, `•`, `●`, `◦`, and `‣` as bullet syntax in the base. The candidate must replace them with Markdown structure.

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

## Typical corrections

- one slide title remains H2 while labels from a web screenshot become H3/list items;
- a sequence of `▶` lines becomes one Markdown list;
- a diagram embed moves next to its related bullet instead of appearing as an isolated raw asset line;
- visually paired label/value blocks become a Markdown table without changing cell text order.

Exact visual reconstruction is impossible in portable Markdown. Prefer the native structures in [native-markdown-layout.md](native-markdown-layout.md) over custom CSS or new visible labels.
