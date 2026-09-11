# Rendering conservation contract

The pre-edit Markdown snapshot is the content authority, whatever produced the note. The overwritten target may change math syntax only. Obsidian renders math with MathJax, so only `$...$` and `$$...$$` are portable; every change this skill makes exists to satisfy that renderer without altering meaning.

There is one Markdown output path. A byte-exact `before.md` snapshot exists only for validation and rollback under the system temporary directory or the installed skill directory. Neither the snapshot nor the report may be placed inside the Obsidian vault, and no second Markdown version may exist in the vault.

## Page boundary

`<!-- source-page: N -->` markers are immutable separator lines when present. The exact marker-line bytes, sequence, numbering, and page count must match. Every transformation occurs inside the closed segment after marker N and before marker N+1. A math span may not cross either marker. A note without page markers is treated as one segment.

## Visible-text conservation

After removing math spans and Markdown-only syntax, the snapshot and the overwritten target must produce the same visible token sequence on every page. Math spans are compared separately as an ordered list of canonical math payloads. Canonicalization removes only the delimiters, environment wrappers, `\label{...}`, and `\nonumber` or `\notag`; it never equates different symbols. When a page disagrees, the report names the first differing span with a short source-versus-refined excerpt.

## Environment equivalence

`align`, `align*`, `aligned`, `eqnarray`, `flalign`, `alignat`, and `split` share one canonical class. `gather`, `gather*`, `gathered`, `multline`, and `multline*` share a second class. `equation`, `equation*`, `displaymath`, and `math` canonicalize to no wrapper. `cases`, `array`, and the matrix environments keep their own identity.

## Redundant display shell

A doubled display fence is the same math written twice. Collapsing it is conservation-neutral, so the shell transform is on by default and the canonical comparison neutralizes it on both sides.

## Asset, link, and metadata conservation

- Frontmatter bytes must be identical.
- Ordinary wikilink and Markdown-link destinations must be unchanged per page.
- Asset embeds must match as a per-page multiset; display-width changes are allowed but the target set is not.
- Source-page comments remain unchanged.
- `lecture-layer:` blocks block the default pass; `--allow-lecture-layers` permits a math-only pass but every other gate still applies.

## Existing Callouts

Callout header lines are compared per page in order. A Callout already present in the snapshot is allowed; do not classify it as user-authored without explicit provenance. Adding, removing, retitling, changing the type or fold state of, or reordering a Callout fails validation. `conversion-layer:` markers must remain byte-identical and in order.

## Rollback and post-run verification

- Validation failure restores the target from the snapshot automatically and byte-for-byte, inside the same process. A handled error does the same.
- Rollback cannot protect the file from another process that writes after the script returns. After a run, recompute the note's `sha256` and compare it to `refined_sha256` in the report.
- If the hashes differ, copy `before.md` back over the note and retry. Quiesce the vault during a run: close Obsidian or pause any sync client so the file is not rewritten mid-run.
- A non-zero exit leaves the run directory in place as a debugging artifact; delete it after the failure is resolved.
- The vault receives no second Markdown version, backup file, report, hidden directory, or hidden temporary file.
