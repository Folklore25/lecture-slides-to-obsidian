---
name: lecture-slides-to-obsidian
description: Convert course PDFs, presentations, policies, and papers through the official MinerU Precision API into self-contained Obsidian document folders containing full Markdown, extracted assets, and a relationship canvas. Use for reusable course materials; source originals and temporary QA reports always remain outside the Obsidian vault.
metadata:
  required-skills: "obsidian-markdown, json-canvas"
  required-services: "MinerU Precision API v4"
---

# Lecture Slides to Obsidian

Prepare a complete, editable course document while keeping the source original outside the vault and retaining derived images or page fallbacks wherever Markdown cannot represent the layout reliably.

## Current implementation status

This phase-one orchestration skill uses the official MinerU Precision API v4 as its only extraction backend and requires `obsidian-markdown` plus `json-canvas` for derived vault artifacts. It performs no local source-document parsing.

## Quick reference

- Explicitly invoke the Skill tool for `obsidian-markdown` and `json-canvas`; availability alone is not loading. Pass both names to `preflight.py --loaded-skill` and record them in temporary QA context.
- Skill-owned state is under the loaded skill directory, for example `~/.claude/skills/lecture-slides-to-obsidian/state/`, `~/.agents/skills/lecture-slides-to-obsidian/state/`, or cc-switch's managed skill directory.
- Run `scripts/preflight.py` first; ask its `questions[]` in stages rather than assuming all inputs.
- `source_pages`: trust `len(content_list_v2)`; fallback to `max(page_idx)+1`. Other counts are diagnostics.
- Signed PUT: raw bytes, no Bearer, explicitly empty Content-Type (`--header 'Content-Type:'`).
- Page marker: `<!-- source-page: N -->` immediately before page N's first included block.
- Canvas `file`: full path relative to vault root, such as `IS6000/Lectures/l01/l01.md`; never a bare filename.
- Render QA with `fill-report.py` under staging, validate with `--report ... --delete-report-on-success`, and never copy the report into the vault.

## Prerequisite preflight

Before remote extraction, read [requirements/skills.yaml](requirements/skills.yaml), [requirements/services.yaml](requirements/services.yaml), [requirements/tools.yaml](requirements/tools.yaml), and [references/requirements.md](references/requirements.md). Verify both Obsidian skills, OpenSSL, the encrypted token store, and the official API contract. If the token store is absent, run `scripts/token-store.py set`; it collects token/passphrase through hidden prompts and writes only encrypted state.

## Core workflow

1. Run `scripts/preflight.py` and ask its questions in stages. Resolve the supplied course through the persistent registry. Read [references/course-routing.md](references/course-routing.md). Confirm near-match folders before creating anything.
2. Derive one self-contained output folder from the matched semester, course, and document slug. Keep every source PDF/PPT/DOC/XLS outside the Obsidian vault. Never auto-route a fuzzy or ambiguous course-folder match.
3. Resolve or confirm a conversion profile (`lecture-notes`, `policy-document`, or `paper`). Read [references/document-profiles.md](references/document-profiles.md).
4. Validate the file against the official API limits, disclose that it will be uploaded to MinerU, confirm both language and OCR explicitly, and unlock the encrypted API token through a hidden passphrase prompt. Read [references/mineru-api.md](references/mineru-api.md).
5. Work in staging. Keep the source unchanged and keep API downloads separate from the Obsidian output.
6. Use the signed-upload and batch-polling flow, then safely unpack the result ZIP.
7. Reconstruct pages with `scripts/reconstruct-note.py` from `content_list_v2.json`; legacy `content_list.json` must first be grouped by `page_idx`. Never locate page boundaries with unscoped `full.md` string anchors. Read [references/mineru-normalization.md](references/mineru-normalization.md).
8. Write the complete Markdown and assets using [references/output-contract.md](references/output-contract.md) and [references/obsidian-style.md](references/obsidian-style.md).
9. Create the relationship canvas with `scripts/build-canvas.py` and [references/canvas-contract.md](references/canvas-contract.md).
10. Render temporary QA with `scripts/fill-report.py`, run [references/validation.md](references/validation.md), extract the facts needed for the final response, delete the report on success, then send the concise summary. Never place the report in the Obsidian vault.

## Non-negotiable boundaries

- Do not claim that source-to-Markdown conversion is lossless. Optimize for semantic fidelity with visual fallback.
- Do not invent missing slide content or normalize an uncertain equation into a confident-looking result.
- Keep links relative and assets portable inside an Obsidian vault.
- Resolve every destination under the registered semester root. Reject absolute child paths, `..` traversal, or a resolved path that escapes the course folder.
- Do not guess when the same course name can refer to multiple semesters or folders.
- Do not copy, move, embed, or symlink source PDFs, presentations, office documents, or archives into the Obsidian vault.
- Keep runtime registry data under this installed skill's `state/` directory. Do not create a user-level config directory elsewhere.
- The user must be told that the source is uploaded to MinerU before encrypted credentials are unlocked. Proceeding with unlock authorizes that upload.
- The API token may persist only as `state/mineru-api-token.enc.json`. Never store plaintext token or passphrase in registry/config, other files, environment profiles, shell history, reports, logs, or Git; never repeat them in responses.
- The encrypted token passphrase is never stored. If it is lost, delete and recreate the encrypted token file.
- Send the Bearer token only to HTTPS endpoints on `mineru.net`. Never attach it to signed upload URLs, CDN result URLs, callbacks, or third-party hosts.
- Treat lecture materials as potentially copyrighted or private. Do not add real course PDFs to this skill repository by default.
- Do not fall back to local PDF parsing, a local MinerU runtime, a similarly named skill, or the unauthenticated lightweight API.

## Supporting resources

- Read [references/requirements.md](references/requirements.md) before invoking prerequisite skills or diagnosing a missing dependency.
- Read [references/mineru-api.md](references/mineru-api.md) before collecting a token, uploading a file, polling, or downloading results.
- Read [references/course-routing.md](references/course-routing.md) whenever registering, matching, moving, or classifying course files.
- Read [references/document-profiles.md](references/document-profiles.md) before shaping a non-slide document.
- Read [references/mineru-normalization.md](references/mineru-normalization.md) before reconstructing pages or headings.
- Read [references/canvas-contract.md](references/canvas-contract.md) before creating a `.canvas` file.
- Read [references/workflow.md](references/workflow.md) for the staged conversion process and failure handling.
- Read [references/output-contract.md](references/output-contract.md) before writing final artifacts.
- Read [references/obsidian-style.md](references/obsidian-style.md) when shaping the lecture note.
- Read [references/quality-gates.md](references/quality-gates.md) before declaring completion.
- Read [references/validation.md](references/validation.md) and run `scripts/validate-output.py` before declaring completion.
- Use [examples/invocations.md](examples/invocations.md) and [examples/expected-note.md](examples/expected-note.md) as synthetic examples, not as rigid templates.
