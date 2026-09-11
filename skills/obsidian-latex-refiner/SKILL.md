---
name: obsidian-latex-refiner
description: Deterministically normalize MinerU-emitted LaTeX in an Obsidian course note so every equation renders with Obsidian's MathJax. Use after extraction or reconstruction and before classroom notes; a script rewrites math delimiters, environments, and CJK runs in place, then a validator restores the snapshot if any conservation gate fails.
metadata:
  required-skills: "obsidian-markdown"
  requires-multimodal: "false"
  deterministic: "true"
---

# Obsidian LaTeX Refiner

Make MinerU LaTeX render in Obsidian without changing what the document says. This skill is deterministic: `scripts/normalize-latex.py` rewrites math syntax, and `scripts/validate-latex-refinement.py` independently proves that visible content is conserved. No vision model is required.

Delimiters, environments, and non-rendering commands change. Visible text, math payloads, page order, links, assets, and Callouts do not.

Each `<!-- source-page: N -->` marker is an immutable boundary. Normalization is page-local: a math span may not cross a marker, and nothing may move between pages.

## Inputs

- target MinerU-derived Markdown in its final vault location;
- byte-exact `before.md` snapshot and `latex-refinement-report.json` under the system temporary directory or the installed skill directory, never inside the vault;
- optional `--no-cjk` when the author prefers raw CJK inside math.

Run only before classroom/student/teacher layers exist. If the Markdown contains `lecture-layer:` markers, or the user identifies later additions, stop. A pre-existing Callout is a conversion artifact, not user authorship; do not ask about it.

## Workflow

1. Confirm the base Markdown is already written to its final path and no `lecture-layer:` marker exists.
2. Create a uniquely named run directory with the platform temporary-directory API; a non-hidden `tmp/` directory inside the installed skill is the fallback. Prove it resolves outside the vault.
3. Run `scripts/normalize-latex.py --target <vault-note.md> --vault-root <vault-root> --snapshot <run-dir>/before.md --report <run-dir>/latex-refinement-report.json`.
4. The script snapshots the target, normalizes math, runs conservation validation, and automatically restores the snapshot on any failure. Do not ask for approval before that rollback.
5. Read the report. If `valid` is false, keep the restored base Markdown and report the failure. On success, keep the overwritten target and the report until final package validation.
6. Delete the snapshot, report, and empty run directory before completion.

Never hand-edit math syntax instead of the script without re-running `scripts/validate-latex-refinement.py`. Treat its report as mandatory evidence.

## Allowed transformations

- `\\(...\\)` and `\begin{math}...\end{math}` to inline `$...$`;
- `\\[...\\]`, `\begin{displaymath}`, and `\begin{equation}...\end{equation}` to display `$$...$$`;
- `align`, `align*`, `eqnarray`, `flalign`, `alignat`, and `split` to `aligned`, and `gather` and `multline` to `gathered`;
- strip non-rendering `\label{...}`, `\nonumber`, and `\notag`;
- wrap a raw CJK run inside math in a text command for upright rendering;
- promote a multiline inline span to display math.

## Forbidden transformations

- changing, correcting, translating, summarizing, or reordering any visible text or math payload;
- adding, removing, or renumbering source-page markers;
- moving text, assets, or links across a page boundary;
- creating, removing, retitling, or reordering Callouts or `conversion-layer:` markers;
- inserting raw HTML, Mermaid, or plugin-specific syntax;
- copying the source PDF into the vault or creating any dot-prefixed path in the vault;
- refining a note after student/teacher additions exist.

## Resources

- Read [references/latex-normalization.md](references/latex-normalization.md) for the exact mapping and review cases.
- Read [references/rendering-contract.md](references/rendering-contract.md) before overwriting the target.
- Use [templates/latex-refinement-task.md](templates/latex-refinement-task.md) when delegating the run to a subagent.
- Treat the validator report as mandatory evidence, not an optional lint result.
