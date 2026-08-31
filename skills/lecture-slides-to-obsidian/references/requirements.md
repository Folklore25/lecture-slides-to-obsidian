# Prerequisite skills

This skill orchestrates two separately installed skills. The machine-readable source of truth is [../requirements/skills.yaml](../requirements/skills.yaml).

## Required skills

### `mineru-pdf`

Use it for PDF inspection and extraction, including reading order, formulas, tables, figures, and OCR. It depends on a working MinerU runtime. Treat network-backed MinerU modes as unavailable unless the user explicitly authorizes uploading the lecture material; prefer the local pipeline.

### `obsidian-markdown`

Use it after extraction to normalize and verify Obsidian Flavored Markdown: properties, wikilinks, embeds, callouts, comments, math delimiters, and vault-relative references. It does not parse PDFs or decide course destinations.

## Preflight

Before opening course content:

1. Inspect the harness's available skill list for exact names `mineru-pdf` and `obsidian-markdown`.
2. Load both skills completely when available.
3. Verify the `mineru` runtime command required by `mineru-pdf` without changing system state.
4. If any check fails, stop before conversion and list each missing skill or runtime with the matching source from `requirements/skills.yaml`.
5. Do not substitute a similarly named skill, silently downgrade extraction, or install anything unless the user requests installation.

The prerequisite manifest is declarative. Agent Skills and cc-switch do not currently provide a portable skill-to-skill automatic installation contract, so enforcement belongs to this preflight and future contract tests.

## Invocation boundary

Use `mineru-pdf` to create raw extraction artifacts in staging. This skill then applies course routing and the shared output contract. Use `obsidian-markdown` for final note shaping and syntax verification. Preserve the warnings and provenance produced by the extractor instead of allowing normalization to hide uncertainty.
