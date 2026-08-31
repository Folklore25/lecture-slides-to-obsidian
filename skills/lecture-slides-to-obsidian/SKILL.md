---
name: lecture-slides-to-obsidian
description: Convert course PDFs, presentations, policies, and papers through the official MinerU Precision API into self-contained Obsidian document folders containing full Markdown, extracted assets, a relationship canvas, and a conversion report. Use for reusable course materials; source originals always remain outside the Obsidian vault.
metadata:
  required-skills: "obsidian-markdown, json-canvas"
  required-services: "MinerU Precision API v4"
---

# Lecture Slides to Obsidian

Prepare a complete, editable course document while keeping the source original outside the vault and retaining derived images or page fallbacks wherever Markdown cannot represent the layout reliably.

## Current implementation status

This phase-one orchestration skill uses the official MinerU Precision API v4 as its only extraction backend and requires `obsidian-markdown` plus `json-canvas` for derived vault artifacts. It performs no local source-document parsing.

## Prerequisite preflight

Before remote extraction, read [requirements/skills.yaml](requirements/skills.yaml), [requirements/services.yaml](requirements/services.yaml), and [references/requirements.md](references/requirements.md). Verify both required Obsidian skills and the official API contract. Collect the MinerU API token from the user as plaintext interactive input only when a request is ready to upload. Never persist or echo it.

## Core workflow

1. Resolve the supplied course name through the persistent course registry. Read [references/course-routing.md](references/course-routing.md). If no course matches, bind it under the valid active semester; ask for the semester root only when no valid active semester exists, then persist both mappings before conversion.
2. Derive one self-contained output folder from the matched semester, course, and document slug. Keep every source PDF/PPT/DOC/XLS outside the Obsidian vault. Never auto-route a fuzzy or ambiguous course-folder match.
3. Resolve or confirm a conversion profile (`lecture-notes`, `policy-document`, or `paper`). Read [references/document-profiles.md](references/document-profiles.md).
4. Validate the file against the official API limits, disclose that it will be uploaded to MinerU, confirm OCR explicitly, and collect the API token in plaintext input. Read [references/mineru-api.md](references/mineru-api.md).
5. Work in staging. Keep the source unchanged and keep API downloads separate from the Obsidian output.
6. Use the signed-upload and batch-polling flow, then safely unpack the result ZIP.
7. Reconstruct pages from `content_list_v2.json`, or legacy `content_list.json` grouped by `page_idx`; never locate page boundaries with unscoped `full.md` string anchors. Read [references/mineru-normalization.md](references/mineru-normalization.md).
8. Write the complete Markdown and assets using [references/output-contract.md](references/output-contract.md) and [references/obsidian-style.md](references/obsidian-style.md).
9. Create the relationship canvas using [references/canvas-contract.md](references/canvas-contract.md).
10. Run [references/validation.md](references/validation.md) and the quality gates. Fill [templates/conversion-report.md](templates/conversion-report.md); record unresolved and not-checked items explicitly.

## Non-negotiable boundaries

- Do not claim that source-to-Markdown conversion is lossless. Optimize for semantic fidelity with visual fallback.
- Do not invent missing slide content or normalize an uncertain equation into a confident-looking result.
- Keep links relative and assets portable inside an Obsidian vault.
- Resolve every destination under the registered semester root. Reject absolute child paths, `..` traversal, or a resolved path that escapes the course folder.
- Do not guess when the same course name can refer to multiple semesters or folders.
- Do not copy, move, embed, or symlink source PDFs, presentations, office documents, or archives into the Obsidian vault.
- Keep runtime registry data under this installed skill's `state/` directory. Do not create a user-level config directory elsewhere.
- The user must be told that the PDF is uploaded to MinerU before the API token is requested. Supplying the token for the conversion authorizes that upload.
- API tokens are session-only secrets. Never save them in registry/config/state, files, environment profiles, shell history, reports, logs, or Git; never repeat them in responses.
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
