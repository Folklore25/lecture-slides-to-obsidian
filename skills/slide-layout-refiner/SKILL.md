---
name: slide-layout-refiner
description: Optionally refine the readability and page-local layout of MinerU-derived slide Markdown by comparing it with the original PDF using a multimodal model. Use only after extraction and before user notes; preserve all content, text order, page order, and per-page assets.
metadata:
  required-skills: "obsidian-markdown"
  preferred-model: "MiniMax-M3"
  requires-multimodal: "true"
---

# Slide Layout Refiner

Restore readable slide structure after MinerU extraction without changing what the source says. This skill is optional and disabled by default.

Each `<!-- source-page: N -->` marker is an immutable slide boundary. Optimize only the content between two adjacent markers; never merge, split, move, regenerate, or restyle the markers themselves.

## Inputs

- original PDF outside the vault;
- base MinerU-derived Markdown under staging;
- normalized document-local assets;
- candidate output path under staging;
- optional page-group JSON for provenance diagnostics.

Run only before classroom/student/teacher layers exist. If the Markdown contains `lecture-layer:` markers or user-authored additions, stop rather than reformatting them.

## Workflow

1. Confirm the option is enabled and the selected model is multimodal. Prefer `MiniMax-M3` as requested. If the runtime cannot provide the original PDF visually, skip refinement and keep the base Markdown; do not use a text-only guess.
2. Read [references/refinement-contract.md](references/refinement-contract.md).
3. Read [references/native-markdown-layout.md](references/native-markdown-layout.md), then give one PDF and its base Markdown to a visual-layout subagent using [templates/multimodal-layout-task.md](templates/multimodal-layout-task.md).
4. The subagent writes a candidate Markdown file only. It must not overwrite the base or final note.
5. Run `scripts/validate-layout-refinement.py --base ... --candidate ... --report ...`.
6. Accept the candidate only when every conservation gate passes. Otherwise preserve the base Markdown unchanged and report the rejected differences.

## Allowed transformations

- identify the true slide title from the PDF and adjust heading levels;
- demote MinerU's fragmented pseudo-H2 blocks to H3, paragraph, list, or table structure;
- convert decorative bullet glyphs such as `▶`, `►`, `▪`, or `•` into Markdown lists;
- join visually continuous lines into paragraphs without changing token order;
- represent faithful hierarchy/grouping with native headings, nested/ordered lists, tables, blockquotes, emphasis, highlights, embeds, and whitespace;
- move or resize an existing asset embed within its original source page so it sits beside the content it explains.

## Forbidden transformations

- changing, correcting, translating, summarizing, or adding visible text;
- fixing OCR/spelling, even when the PDF suggests a correction;
- reordering text tokens or source pages;
- moving assets across page markers, removing assets, or inventing captions;
- adding callout titles, explanations, links, or source metadata not present in the base;
- using raw HTML, custom CSS, Mermaid, or other non-native layout workarounds;
- copying the original PDF into the vault;
- refining a note after student/teacher additions exist.

## Resources

- Read [references/refinement-contract.md](references/refinement-contract.md) before generating a candidate.
- Read [references/native-markdown-layout.md](references/native-markdown-layout.md) for H1–H4 allocation and syntax selection.
- Use [templates/multimodal-layout-task.md](templates/multimodal-layout-task.md) for the visual subagent.
- Treat the validator report as mandatory evidence, not an optional lint result.
