---
name: lecture-slides-to-obsidian
description: Route Canvas or local lecture-slide PDFs into registered semester and course folders, submit them to the official MinerU Precision API, then produce structured Obsidian Markdown with provenance, assets, and visual fallbacks. Use when preparing reusable pre-class lecture notes; not for offline conversion, exact PDF reconstruction, or general PDF editing.
metadata:
  required-skills: "obsidian-markdown"
  required-services: "MinerU Precision API v4"
---

# Lecture Slides to Obsidian

Prepare an editable lecture note that preserves the meaning of the slides and keeps the source PDF or page images available wherever Markdown cannot represent the layout reliably.

## Current implementation status

This phase-one orchestration skill uses the official MinerU Precision API v4 as its only PDF extraction backend and requires the `obsidian-markdown` skill for final note shaping. It performs no local PDF content parsing.

## Prerequisite preflight

Before remote extraction, read [requirements/skills.yaml](requirements/skills.yaml), [requirements/services.yaml](requirements/services.yaml), and [references/requirements.md](references/requirements.md). Verify the required Obsidian skill and official API contract. Collect the MinerU API token from the user as plaintext interactive input only when a request is ready to upload. Never persist or echo it.

## Core workflow

1. Resolve the supplied course name through the persistent course registry. Read [references/course-routing.md](references/course-routing.md). If no course matches, bind it under the valid active semester; ask for the semester root only when no valid active semester exists, then persist both mappings before conversion.
2. Derive the destination from the matched semester, course folder, and registered subfolder roles. Never auto-route a fuzzy or ambiguous match.
3. Validate the file against the official API limits, disclose that the file will be uploaded to MinerU, and collect the API token in plaintext input. Read [references/mineru-api.md](references/mineru-api.md).
4. Work in a staging directory. Keep the source PDF unchanged and keep API downloads separate from the final Obsidian note.
5. Use the official signed-upload and batch-polling flow. Safely unpack the returned ZIP and preserve `full.md`, images, JSON, page boundaries, and API warnings as raw extraction artifacts.
6. Normalize the result using [references/output-contract.md](references/output-contract.md) and [references/obsidian-style.md](references/obsidian-style.md).
7. Preserve a visual fallback for diagrams, dense layouts, handwritten annotations, or any page whose structure cannot be represented confidently in Markdown.
8. Apply [references/quality-gates.md](references/quality-gates.md). Record unresolved issues in the conversion report instead of presenting them as correct.
9. Report the matched semester/course, created note, classified source/assets/report paths, fallback pages, warnings, and any manual review still required.

## Non-negotiable boundaries

- Do not claim that PDF-to-Markdown conversion is lossless. Optimize for semantic fidelity with visual fallback.
- Do not invent missing slide content or normalize an uncertain equation into a confident-looking result.
- Keep links relative and assets portable inside an Obsidian vault.
- Resolve every destination under the registered semester root. Reject absolute child paths, `..` traversal, or a resolved path that escapes the course folder.
- Do not guess when the same course name can refer to multiple semesters or folders.
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
- Read [references/workflow.md](references/workflow.md) for the staged conversion process and failure handling.
- Read [references/output-contract.md](references/output-contract.md) before writing final artifacts.
- Read [references/obsidian-style.md](references/obsidian-style.md) when shaping the lecture note.
- Read [references/quality-gates.md](references/quality-gates.md) before declaring completion.
- Use [examples/invocations.md](examples/invocations.md) and [examples/expected-note.md](examples/expected-note.md) as synthetic examples, not as rigid templates.
