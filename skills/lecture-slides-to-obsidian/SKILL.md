---
name: lecture-slides-to-obsidian
description: Route Canvas or local lecture-slide PDFs into registered semester and course folders, then convert them into structured Obsidian Markdown with page provenance, extracted assets, and visual fallbacks. Use when preparing reusable pre-class lecture notes; not for exact PDF reconstruction or general PDF editing.
---

# Lecture Slides to Obsidian

Prepare an editable lecture note that preserves the meaning of the slides and keeps the source PDF or page images available wherever Markdown cannot represent the layout reliably.

## Current implementation status

This phase-one skill requires filesystem access and a PDF extraction backend selected at runtime. It does not bundle an extraction engine yet.

## Core workflow

1. Resolve the supplied course name through the persistent course registry. Read [references/course-routing.md](references/course-routing.md). If no course matches, bind it under the valid active semester; ask for the semester root only when no valid active semester exists, then persist both mappings before conversion.
2. Derive the destination from the matched semester, course folder, and registered subfolder roles. Never auto-route a fuzzy or ambiguous match.
3. Inspect the PDF and available local tools before selecting a conversion path. Read [references/engine-adapters.md](references/engine-adapters.md) when choosing or integrating an extraction backend.
4. Work in a staging directory. Keep the source PDF unchanged and keep intermediate files separate from the final Obsidian note.
5. Extract text, headings, lists, equations, tables, images, and page boundaries with provenance. Never silently repair uncertain text, symbols, or reading order.
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
- Do not upload course PDFs or extracted content to a network service unless the user explicitly authorizes it.
- Treat lecture materials as potentially copyrighted or private. Do not add real course PDFs to this skill repository by default.
- No conversion engine is bundled in this phase. Do not call nonexistent scripts or claim a conversion ran; use an available, user-approved backend or stop with a precise requirement.

## Supporting resources

- Read [references/course-routing.md](references/course-routing.md) whenever registering, matching, moving, or classifying course files.
- Read [references/workflow.md](references/workflow.md) for the staged conversion process and failure handling.
- Read [references/output-contract.md](references/output-contract.md) before writing final artifacts.
- Read [references/obsidian-style.md](references/obsidian-style.md) when shaping the lecture note.
- Read [references/engine-adapters.md](references/engine-adapters.md) only when selecting or adding a backend.
- Read [references/quality-gates.md](references/quality-gates.md) before declaring completion.
- Use [examples/invocations.md](examples/invocations.md) and [examples/expected-note.md](examples/expected-note.md) as synthetic examples, not as rigid templates.
