---
name: lecture-slides-to-obsidian
description: Compose the official MinerU Open API CLI with Obsidian skills to convert external course documents into complete Markdown, derived assets, and a delegated knowledge-recall Canvas. Use for extraction or Markdown reconstruction; when complete Markdown already exists and only Canvas is requested, invoke obsidian-canvas-designer directly instead.
metadata:
  required-skills: "obsidian-markdown, obsidian-cli, obsidian-canvas-designer"
  optional-skills: "slide-layout-refiner"
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
- Optional slide-layout refinement is disabled by default. When enabled, first write the base note to its final path, then delegate the original PDF plus that note to `slide-layout-refiner` with a model that supports visual input. It directly overwrites the same note, preserves every source-page boundary, and rolls back from an outside-vault snapshot if validation fails.
- Canvas: delegate the complete drawing task to `obsidian-canvas-designer`; the main Agent supplies the note, semantic model, assets, paths, and overwrite boundary, then consumes only its artifacts and PASS/FAIL evidence.
- Multi-file Canvas rule: count unique Canvas work items before delegation. For two or more files, announce the batch plan, create one Canvas subagent task per file, and never combine multiple notes in one drawing subagent. Follow [references/canvas-batch-delegation.md](references/canvas-batch-delegation.md).
- Canvas `file`: full path relative to vault root, such as `<course>/Lectures/<document>/<document>.md`; never a bare filename.
- Asset name: `page-<PPP>-<figure|table|equation|chart|fallback>-<NN>.<ext>`, for example `page-004-figure-01.png`.
- Put all staging/QA state under the system temporary directory or a non-hidden `tmp/` directory inside the installed skill. Render QA with `fill-report.py`, validate with `--report ... --recall-model ... --delete-qa-on-success`, and never copy temporary QA state into the vault.

## Prerequisite preflight

Before extraction, read [requirements/skills.yaml](requirements/skills.yaml), [requirements/services.yaml](requirements/services.yaml), [requirements/tools.yaml](requirements/tools.yaml), and [references/requirements.md](references/requirements.md). Verify the note/CLI skills, Canvas designer subskill, local render profile, `mineru-open-api`, OpenSSL, macOS Keychain, and encrypted token state. If token state is absent, pass the chat-provided token to `scripts/token-store.py set --token-stdin` through stdin. Later runs unlock automatically.

## Core workflow

1. Run `scripts/preflight.py` and ask its questions in stages. Resolve the supplied course through the persistent registry. Read [references/course-routing.md](references/course-routing.md). Confirm near-match folders before creating anything.
2. Derive one self-contained output folder from the matched semester, course, and document slug. Keep every source PDF/PPT/DOC/XLS outside the Obsidian vault. Never auto-route a fuzzy or ambiguous course-folder match.
3. Resolve or confirm a conversion profile (`lecture-notes`, `policy-document`, or `paper`). Read [references/document-profiles.md](references/document-profiles.md).
4. Validate the file against MinerU limits, disclose the network upload, and confirm language/OCR. Read [references/mineru-cli.md](references/mineru-cli.md).
5. Work in a uniquely named system temporary directory, falling back to a non-hidden `tmp/` directory inside the installed skill. Keep the source unchanged and keep official CLI outputs separate from the Obsidian output. Never create staging, cache, backup, report, or other dot-prefixed paths in the vault.
6. Run `scripts/mineru-cli-adapter.py`; it injects the Keychain token through `MINERU_TOKEN`, calls official precision extraction with `md,json`, and produces a page-group compatibility file.
7. Reconstruct pages with `scripts/reconstruct-note.py` from the adapter's normalized page groups. Never locate page boundaries with unscoped Markdown string anchors. Read [references/mineru-normalization.md](references/mineru-normalization.md).
8. Write the base Markdown to its final path. If optional visual-layout refinement is enabled, load `slide-layout-refiner`, snapshot the note outside the vault, and delegate the source PDF plus that target path to a multimodal subagent. The subagent directly overwrites the target. Validate the overwrite; on failure the validator restores the snapshot automatically. Never cross or alter source-page markers.
9. Write the complete Markdown and assets using [references/output-contract.md](references/output-contract.md) and [references/obsidian-style.md](references/obsidian-style.md).
10. Read each complete note and allocate one isolated staging/output tuple per Canvas. Run `scripts/plan-canvas-batch.py`. With one item, direct execution or one subagent is allowed; with two or more, create one subagent task per item. Parallelize authoring/build/aesthetic within available capacity, then serialize real Obsidian DOM work through one renderer slot. Require aesthetic, measurement, and final render-check artifacts per file.
11. Render temporary QA with `scripts/fill-report.py`, run [references/validation.md](references/validation.md) over the Canvas subagent's returned files, extract the facts needed for the final response, delete all QA state on success, then send the concise summary. Never place QA files in the Obsidian vault.

## Non-negotiable boundaries

- Do not claim that source-to-Markdown conversion is lossless. Optimize for semantic fidelity with visual fallback.
- Do not invent missing slide content or normalize an uncertain equation into a confident-looking result.
- Keep links relative and assets portable inside an Obsidian vault.
- Resolve every destination under the registered semester root. Reject absolute child paths, `..` traversal, or a resolved path that escapes the course folder.
- Do not guess when the same course name can refer to multiple semesters or folders.
- Do not copy, move, embed, or symlink source PDFs, presentations, office documents, or archives into the Obsidian vault.
- Do not create `.staging`, `.tmp`, `.cache`, backup directories, second Markdown versions, or any other dot-prefixed path in the Obsidian vault. Existing application-owned paths such as `.obsidian/` are out of scope and must not be modified for this workflow.
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
- Load [../slide-layout-refiner/SKILL.md](../slide-layout-refiner/SKILL.md) only when optional multimodal slide-layout refinement is enabled.
- Load [../obsidian-canvas-designer/SKILL.md](../obsidian-canvas-designer/SKILL.md) and delegate all Canvas creation or visual refinement to that skill.
- Read [references/canvas-batch-delegation.md](references/canvas-batch-delegation.md) whenever two or more Canvas work items are present.
- Read [references/workflow.md](references/workflow.md) for the staged conversion process and failure handling.
- Read [references/output-contract.md](references/output-contract.md) before writing final artifacts.
- Read [references/obsidian-style.md](references/obsidian-style.md) when shaping the lecture note.
- Read [references/quality-gates.md](references/quality-gates.md) before declaring completion.
- Read [references/validation.md](references/validation.md) and run `scripts/validate-output.py` before declaring completion.
- Use [examples/invocations.md](examples/invocations.md) and [examples/expected-note.md](examples/expected-note.md) as synthetic examples, not as rigid templates.
