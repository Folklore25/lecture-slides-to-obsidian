---
name: obsidian-latex-refiner
description: Fix LaTeX math in an Obsidian note so every equation renders with Obsidian's MathJax. Works on any source (MinerU, LaTeXML, pandoc, LLM output, or hand-written). The agent first scans the note read-only, decides which normalizations are safe, then applies them in place while an independent validator proves content conservation and restores the snapshot on any failure.
metadata:
  required-skills: "obsidian-markdown"
  requires-multimodal: "false"
  deterministic: "true"
  agent-driven: "true"
---

# Obsidian LaTeX Refiner

Make equations render in Obsidian without changing what the document says. The transform is content-conserving and source-agnostic: it normalizes math syntax only.

This skill is **agent-driven**. Do not run the fix blindly. Scan the note read-only, read the reported issues, decide which transform groups are safe for this document, then apply them. A separate validator independently proves conservation and restores the byte-exact snapshot on any failure.

## Workflow

1. **Scan (read-only).** Run `scripts/normalize-latex.py --target <note> --analyze [--report <run-dir>/analysis.json]`. It changes nothing and reports per page the math spans, delimiter styles, environments, and issues such as `redundant_display_shell`, `legacy_inline_delimiter`, `raw_cjk_in_math`, `unbalanced_dollar`, and `document_latex_*`, plus `recommended_transforms`.
2. **Decide.** Read the analysis and choose the transform groups with `--only`, or accept the recommendation. Handle `review_items` (document-level LaTeX such as `\begin{table}`, `\includegraphics`, `\href`) manually; the script never guesses at those.
3. **Preview when unsure.** Add `--dry-run` to write the proposed Markdown next to the snapshot without touching the note.
4. **Apply.** Run `scripts/normalize-latex.py --target <note> --snapshot <run-dir>/before.md --report <run-dir>/latex-refinement-report.json [--only ...]`. The script writes the byte-exact snapshot, normalizes math, validates conservation, and restores the snapshot on any failure.
5. **Verify.** Read the report, or use `--report-format text` for a human summary. When `valid` is false the note has already been restored; report the failure and do not hand-edit. When it is true, keep the report until final package validation.
6. **Confirm on disk.** After the script exits, recompute the note's `sha256` and compare it to `refined_sha256` in the report. A different hash means another process (Obsidian auto-save, a sync client, a file watcher) rewrote the file after the script returned; copy `<run-dir>/before.md` back and retry on a quiet vault.
7. Delete the snapshot, analysis, and report after final validation.

## Transform groups

| Group | Changes |
| --- | --- |
| `shell` | collapse a doubled display fence (a `$$` line immediately followed by another `$$`) into one |
| `delimiters` | `\(...\)` and `\begin{math}` to inline math; `\[...\]` and `\begin{displaymath}` to display math |
| `environments` | unwrap `equation`, rename `align`, `eqnarray`, `flalign`, `alignat`, `split` to `aligned`, `gather` and `multline` to `gathered`, wrap bare matrix environments |
| `labels` | strip non-rendering `\label{}`, `\nonumber`, `\notag` |
| `cjk` | wrap a raw CJK run inside math in a text command |
| `multiline-inline` | promote a multiline inline span to display math |

## Boundaries

Each `<!-- source-page: N -->` marker is immutable. Normalization is page-local: a math span may not cross a marker, and nothing may move between pages.

By default the note must not contain `lecture-layer:` blocks, because an in-place rewrite must not touch classroom additions. Pass `--allow-lecture-layers` for a math-only pass on such a note; conservation is still enforced, so a transform that touched classroom text would still fail and roll back. A pre-existing Callout is a conversion artifact, not user authorship; only explicit `lecture-layer:` provenance triggers this rule.

Never change visible text, math payloads, page markers, links, assets, or Callouts. Never insert raw HTML, Mermaid, or plugin-specific syntax. Never copy the source PDF into the vault or create a dot-prefixed path in the vault.

## Resources

- Read [references/latex-normalization.md](references/latex-normalization.md) for the full mapping and review cases.
- Read [references/rendering-contract.md](references/rendering-contract.md) before overwriting the target.
- Run `scripts/self-check.py` to smoke-test the bundled fixtures on this machine without touching any vault.
- Use [templates/latex-refinement-task.md](templates/latex-refinement-task.md) when delegating the run to a subagent.
