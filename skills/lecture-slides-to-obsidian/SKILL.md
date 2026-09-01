---
name: lecture-slides-to-obsidian
description: Compose the official MinerU Open API CLI with Obsidian skills to convert external course documents into complete Markdown, derived assets, and a delegated knowledge-recall Canvas. Use for extraction or Markdown reconstruction; when complete Markdown already exists and only Canvas is requested, invoke obsidian-canvas-designer directly instead.
metadata:
  required-skills: "obsidian-markdown, obsidian-cli, obsidian-canvas-designer"
  required-services: "MinerU Precision API via official mineru-open-api CLI"
---

# Lecture Slides to Obsidian

Prepare a complete, editable course document while keeping the source original outside the vault and retaining derived images or page fallbacks wherever Markdown cannot represent the layout reliably.

## Current implementation status

This skill is a thin composition layer. The official `mineru-open-api` CLI owns extraction/network behavior; `obsidian-markdown` and `obsidian-cli` own note syntax and vault operations; `obsidian-canvas-designer` owns Canvas design and renderer QA. This skill owns routing, profile normalization, semantic recall modeling, delegation, vault boundaries, and final package QA.

## Quick reference

- Route by requested artifact before preflight: external source requiring extraction → full workflow; existing normalized page groups requiring Markdown → reconstruction only; complete Markdown requiring only Canvas → stop this skill and invoke `obsidian-canvas-designer` directly.
- Explicitly invoke `obsidian-markdown`, `obsidian-cli`, and `obsidian-canvas-designer`; availability alone is not loading. Pass all three names to `preflight.py --loaded-skill` and record them in temporary QA context.
- Skill-owned state is always under `<installed-skill-directory>/state/`. Prefer cc-switch for installation and lifecycle management; do not assume a runtime-specific home path.
- Run `scripts/preflight.py` first; ask its `questions[]` in stages rather than assuming all inputs.
- `source_pages`: trust the adapter's normalized page-group length (`max(page_idx)+1` from official CLI JSON). Other counts are diagnostics.
- Extraction: run `scripts/mineru-cli-adapter.py`; never reproduce the CLI's HTTP, upload, or polling logic.
- Page marker: `<!-- source-page: N -->` immediately before page N's first included block.
- Canvas: delegate the complete drawing task to `obsidian-canvas-designer`; the main Agent supplies the note, semantic model, assets, paths, and overwrite boundary, then consumes only its artifacts and PASS/FAIL evidence.
- Canvas `file`: full path relative to vault root, such as `<course>/Lectures/<document>/<document>.md`; never a bare filename.
- Asset name: `page-<PPP>-<figure|table|equation|chart|fallback>-<NN>.<ext>`, for example `page-004-figure-01.png`.
- Render QA with `fill-report.py` under staging, validate with `--report ... --recall-model ... --delete-qa-on-success`, and never copy temporary QA state into the vault.

## Prerequisite preflight

Before extraction, read [requirements/skills.yaml](requirements/skills.yaml), [requirements/services.yaml](requirements/services.yaml), [requirements/tools.yaml](requirements/tools.yaml), and [references/requirements.md](references/requirements.md). Verify the note/CLI skills, Canvas designer subskill, local render profile, `mineru-open-api`, OpenSSL, macOS Keychain, and encrypted token state. If token state is absent, pass the chat-provided token to `scripts/token-store.py set --token-stdin` through stdin. Later runs unlock automatically.

## Core workflow

1. Run `scripts/preflight.py` and ask its questions in stages. Resolve the supplied course through the persistent registry. Read [references/course-routing.md](references/course-routing.md). Confirm near-match folders before creating anything.
2. Derive one self-contained output folder from the matched semester, course, and document slug. Keep every source PDF/PPT/DOC/XLS outside the Obsidian vault. Never auto-route a fuzzy or ambiguous course-folder match.
3. Resolve or confirm a conversion profile (`lecture-notes`, `policy-document`, or `paper`). Read [references/document-profiles.md](references/document-profiles.md).
4. Validate the file against MinerU limits, disclose the network upload, and confirm language/OCR. Read [references/mineru-cli.md](references/mineru-cli.md).
5. Work in staging. Keep the source unchanged and keep official CLI outputs separate from the Obsidian output.
6. Run `scripts/mineru-cli-adapter.py`; it injects the Keychain token through `MINERU_TOKEN`, calls official precision extraction with `md,json`, and produces a page-group compatibility file.
7. Reconstruct pages with `scripts/reconstruct-note.py` from the adapter's normalized page groups. Never locate page boundaries with unscoped Markdown string anchors. Read [references/mineru-normalization.md](references/mineru-normalization.md).
8. Write the complete Markdown and assets using [references/output-contract.md](references/output-contract.md) and [references/obsidian-style.md](references/obsidian-style.md).
9. Read the complete note and write staging `recall-model.json` following the Canvas designer's model contract. Delegate Canvas drawing with the exact inputs/outputs in [../obsidian-canvas-designer/references/delegation-contract.md](../obsidian-canvas-designer/references/delegation-contract.md). Require aesthetic, measurement, and final render-check artifacts.
10. Render temporary QA with `scripts/fill-report.py`, run [references/validation.md](references/validation.md) over the Canvas subagent's returned files, extract the facts needed for the final response, delete all QA state on success, then send the concise summary. Never place QA files in the Obsidian vault.

## Non-negotiable boundaries

- Do not claim that source-to-Markdown conversion is lossless. Optimize for semantic fidelity with visual fallback.
- Do not invent missing slide content or normalize an uncertain equation into a confident-looking result.
- Keep links relative and assets portable inside an Obsidian vault.
- Resolve every destination under the registered semester root. Reject absolute child paths, `..` traversal, or a resolved path that escapes the course folder.
- Do not guess when the same course name can refer to multiple semesters or folders.
- Do not copy, move, embed, or symlink source PDFs, presentations, office documents, or archives into the Obsidian vault.
- Keep runtime registry data under this installed skill's `state/` directory. Do not create a user-level config directory elsewhere.
- The initial request to convert through MinerU plus the user-supplied token authorizes future automatic credential use for this skill. Do not request repeated conversational consent.
- The API token may persist only as ciphertext at `state/mineru-api-token.enc.json`; its wrapping key lives only in macOS Keychain. Never store plaintext in registry/config, other files, environment profiles, shell history, reports, logs, or Git; never repeat it in responses.
- Pass the token only through the `MINERU_TOKEN` child-process environment. Never use CLI `--token`, `mineru-open-api auth`, verbose HTTP logging, or direct MinerU HTTP calls.
- Treat lecture materials as potentially copyrighted or private. Do not add real course PDFs to this skill repository by default.
- Do not fall back to local PDF parsing, a local MinerU runtime, a similarly named skill, or the unauthenticated lightweight API.

## Supporting resources

- Read [references/requirements.md](references/requirements.md) before invoking prerequisite skills or diagnosing a missing dependency.
- Read [references/mineru-cli.md](references/mineru-cli.md) before extraction or CLI troubleshooting.
- Read [references/course-routing.md](references/course-routing.md) whenever registering, matching, moving, or classifying course files.
- Read [references/document-profiles.md](references/document-profiles.md) before shaping a non-slide document.
- Read [references/mineru-normalization.md](references/mineru-normalization.md) before reconstructing pages or headings.
- Read [references/asset-naming.md](references/asset-naming.md) before copying, generating, linking, or validating visual assets.
- Load [../obsidian-canvas-designer/SKILL.md](../obsidian-canvas-designer/SKILL.md) and delegate all Canvas creation or visual refinement to that skill.
- Read [references/workflow.md](references/workflow.md) for the staged conversion process and failure handling.
- Read [references/output-contract.md](references/output-contract.md) before writing final artifacts.
- Read [references/obsidian-style.md](references/obsidian-style.md) when shaping the lecture note.
- Read [references/quality-gates.md](references/quality-gates.md) before declaring completion.
- Read [references/validation.md](references/validation.md) and run `scripts/validate-output.py` before declaring completion.
- Use [examples/invocations.md](examples/invocations.md) and [examples/expected-note.md](examples/expected-note.md) as synthetic examples, not as rigid templates.
