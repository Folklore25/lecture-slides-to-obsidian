---
name: slide-layout-refiner
description: Optionally refine the readability and page-local layout of MinerU-derived slide Markdown by comparing it with the original PDF using a multimodal model. Use only after extraction and before user notes; preserve all content, text order, page order, and per-page assets.
metadata:
  required-skills: "obsidian-markdown"
  requires-multimodal: "true"
  requires-visual-input: "true"
---

# Slide Layout Refiner

Restore readable slide structure after MinerU extraction without changing what the source says. The priority is complete information preservation and reading clarity, not pixel-perfect reconstruction. This skill is optional and disabled by default.

Each `<!-- source-page: N -->` marker is an immutable slide boundary. Optimize only the content between two adjacent markers; never merge, split, move, regenerate, or restyle the markers themselves.

## Inputs

- original PDF outside the vault;
- target MinerU-derived Markdown in its final vault location;
- normalized document-local assets;
- an exact pre-edit snapshot and validation report under the system temporary directory or the installed skill directory, never under the vault;
- optional page-group JSON for provenance diagnostics.

Run only before classroom/student/teacher layers exist. If the Markdown contains `lecture-layer:` markers, or the user explicitly identifies later additions, stop rather than reformatting them. A pre-existing Callout is not evidence of user authorship: conversion warnings and fallback tables may legitimately use Callouts. Do not ask the user how to handle a file merely because it already contains Callout syntax.

## Workflow

1. Confirm the option is enabled and the selected model supports visual input. It must be able to inspect the original PDF directly or inspect page images rendered from it. If neither visual input path is available, skip refinement and keep the base Markdown; do not use a text-only guess.
2. Read [references/refinement-contract.md](references/refinement-contract.md).
3. Create a uniquely named run directory with the platform temporary-directory API. A non-hidden `tmp/` directory inside the installed skill is the fallback. Resolve the path and prove it is outside the vault; never create `.tmp`, `.staging`, `.cache`, or any other dot-prefixed path in the vault.
4. Copy the target Markdown byte-for-byte to `<run-dir>/before.md`. This is a rollback snapshot, not a second output version.
5. Read [references/native-markdown-layout.md](references/native-markdown-layout.md), then give one PDF and the target Markdown to a visual-layout subagent using [templates/multimodal-layout-task.md](templates/multimodal-layout-task.md).
6. The subagent directly overwrites the target Markdown. It must not create another Markdown copy in the vault.
7. Run `scripts/validate-layout-refinement.py --snapshot <run-dir>/before.md --target <vault-note.md> --vault-root <vault-root> --report <run-dir>/layout-refinement-report.json`.
8. The validator automatically restores the snapshot when any conservation gate fails; do not ask for approval before this rollback. On success, keep only the overwritten target and retain the report only until final package validation. Delete the snapshot, report, and empty run directory before completion.

When the snapshot already contains Callouts, continue automatically and preserve every Callout header line exactly. The refiner may improve surrounding page structure but must not create, remove, retitle, change the type/fold state of, or reorder a Callout. Only explicit lecture-layer provenance or known later additions trigger the stop rule.

## Allowed transformations

- identify the true slide title from the PDF and adjust heading levels;
- demote MinerU's fragmented pseudo-H2 blocks to H3, paragraph, list, or table structure;
- convert decorative bullet glyphs such as `▶`, `►`, `▪`, or `•` into Markdown lists;
- convert MinerU's line-leading escaped `\-` into real `-` list items; for genuine nested hierarchy, indent each child level with exactly four ASCII spaces before `- ` and never use a Tab character;
- join visually continuous lines into paragraphs without changing token order;
- represent faithful hierarchy/grouping with native headings, nested/ordered lists, tables, blockquotes, emphasis, highlights, embeds, and whitespace;
- move or resize an existing asset embed within its original source page so it sits beside the content it explains.

## Forbidden transformations

- changing, correcting, translating, summarizing, or adding visible text;
- fixing OCR/spelling, even when the PDF suggests a correction;
- reordering text tokens or source pages;
- moving assets across page markers, removing assets, or inventing captions;
- creating, removing, retitling, changing the type/fold state of, or reordering Callouts;
- using raw HTML, custom CSS, Mermaid, or other non-native layout workarounds;
- copying the original PDF into the vault;
- creating a dot-prefixed directory or temporary file anywhere in the vault;
- refining a note after student/teacher additions exist.

## Resources

- Read [references/refinement-contract.md](references/refinement-contract.md) before overwriting the target.
- Read [references/native-markdown-layout.md](references/native-markdown-layout.md) for H1–H4 allocation and syntax selection.
- Use [templates/multimodal-layout-task.md](templates/multimodal-layout-task.md) for the visual subagent.
- Treat the validator report as mandatory evidence, not an optional lint result.
