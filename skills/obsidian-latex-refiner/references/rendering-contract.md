# Rendering conservation contract

The pre-edit MinerU-derived Markdown snapshot is the content authority. The overwritten target may change math syntax only. Obsidian renders math with MathJax, so only `$...$` and `$$...$$` are portable; every change this skill makes exists to satisfy that renderer without altering meaning.

There is one Markdown output path. A byte-exact `before.md` snapshot exists only for validation and rollback under the system temporary directory or the installed skill directory. Neither the snapshot nor the report may be placed inside the Obsidian vault, and no second Markdown version may exist in the vault.

## Page boundary

`<!-- source-page: N -->` markers are immutable separator lines. The exact marker-line bytes, sequence, numbering, and page count must match. Every transformation occurs inside the closed segment after marker N and before marker N+1. A math span may not cross either marker.

## Visible-text conservation

After removing math spans and Markdown-only syntax, the snapshot and the overwritten target must produce the same visible token sequence on every page. Math spans are compared separately as an ordered list of canonical math payloads. Canonicalization removes only the delimiters, environment wrappers, `\label{...}`, and `\nonumber` or `\notag`; it never equates different symbols.

## Environment equivalence

`align`, `align*`, `aligned`, `eqnarray`, `flalign`, `alignat`, and `split` share one canonical class. `gather`, `gather*`, `gathered`, `multline`, and `multline*` share a second class. `equation`, `equation*`, `displaymath`, and `math` canonicalize to no wrapper. `cases`, `array`, and the matrix environments keep their own identity.

## Asset, link, and metadata conservation

- Frontmatter bytes must be identical.
- Ordinary wikilink and Markdown-link destinations must be unchanged per page.
- Asset embeds must match as a per-page multiset; display-width changes are allowed but the target set is not.
- Source-page comments remain unchanged.
- No `lecture-layer:` markers may exist in either input.

## Existing Callouts

Callout header lines are compared per page in order. A Callout already present in the snapshot is allowed; do not classify it as user-authored without explicit provenance. Adding, removing, retitling, changing the type or fold state of, or reordering a Callout fails validation. `conversion-layer:` markers must remain byte-identical and in order.

## Rollback and temporary-path boundary

- Validation failure restores the target from the snapshot automatically and byte-for-byte.
- Rollback is part of the already-authorized overwrite operation; do not interrupt for another confirmation.
- The vault receives no second Markdown version, backup file, report, hidden directory, or hidden temporary file.
- Delete the snapshot after either successful validation or completed rollback. Delete the report after its result has been consumed.
