---
name: lecture-slides-to-obsidian
description: Convert an external course document into content-driven Obsidian notes by reading the source natively with a multimodal model, optionally aided by the official MinerU Open API CLI, and delegate a knowledge-recall Canvas. Use for extraction or Markdown reconstruction; when complete Markdown already exists and only Canvas is requested, invoke obsidian-canvas-designer directly instead.
metadata:
  required-skills: "obsidian-markdown, obsidian-cli, obsidian-canvas-designer"
  optional-skills: "slide-layout-refiner, obsidian-latex-refiner"
  required-services: "Native multimodal source reading; official mineru-open-api CLI used only as an optional extraction aid"
---

# Lecture Slides to Obsidian

Turn an external course document into readable, content-driven Obsidian notes while keeping the source original outside the vault.

## Core model

| Decision | Values | Who decides |
| --- | --- | --- |
| `--extraction` | `native` (default), `mineru` | Agent, from the model's own capability |
| `--note-granularity` | `single-note`, `section-notes` | **The user. Every conversion. Always ask.** |
| profile | `lecture-notes`, `policy-document`, `paper` | Agent proposes, user confirms |

- **`native` is the default.** A natively multimodal model reads the source PDF or slide deck page by page and writes the notes itself. No upload, no token, no text-layer dependency. This is how the reference-quality conversions were produced.
- **`mineru` is an aid, not a gate.** Use it when the model wants machine-readable page groups, when a document is long or heavily scanned, or when the user asks for it. It never replaces the model's own reading.
- **Page markers exist only in MinerU mode.** A note produced from a MinerU transcription may carry `<!-- source-page: N -->`. A note produced natively must not: the page ledger carries coverage instead.

## Quick reference

- Route by requested artifact before preflight: external source requiring conversion → full workflow; complete Markdown requiring only Canvas → stop and invoke `obsidian-canvas-designer` directly.
- Explicitly load `obsidian-markdown`, `obsidian-cli`, and `obsidian-canvas-designer`; availability alone is not loading. Pass all three to `preflight.py --loaded-skill`.
- `<installed-skill-directory>` is the directory containing this SKILL.md; every `scripts/` and `state/` path resolves against it.
- Run `scripts/preflight.py` first; ask its `questions[]` in stages. It always emits a `note_granularity` question for `lecture-notes` and a `native_visual_input` question when extraction is native.
- MinerU token handling applies only with `--extraction mineru`. Run `scripts/token-store.py status` before asking for a token; `configured` means unlock and use it silently.
- Anchor the outline with `scripts/plan-note-structure.py`. Pass `--page-count` for native reading or `--page-groups` when MinerU ran. It drafts `note-plan.json` plus `page-ledger.json`; the Agent corrects both and sets `draft: false`.
- Write one note per entry in `note-plan.json`. H2 headings must equal the planned section headings, so the Canvas keeps a real anchor.
- Assets use lowercase semantic kebab-case names (`qualitative-research-cycle.png`). `page-PPP-kind-NN.ext` survives only in MinerU-mode transcription.
- Canvas: delegate to `obsidian-canvas-designer` with the note, semantic model, assets, paths, and overwrite boundary; consume only its artifacts and PASS/FAIL evidence.
- Multi-note Canvas rule: one Canvas per note, one subagent per note for two or more notes. Follow [references/canvas-batch-delegation.md](references/canvas-batch-delegation.md).
- Put all staging/QA state under the system temporary directory or a non-hidden `tmp/` directory inside the installed skill. Validate with `--report ... --delete-qa-on-success` and never copy QA state into the vault.

## Prerequisite preflight

Read [requirements/skills.yaml](requirements/skills.yaml), [requirements/services.yaml](requirements/services.yaml), [requirements/tools.yaml](requirements/tools.yaml), and [references/requirements.md](references/requirements.md). In native mode the hard requirements are the note/CLI skills, the Canvas designer, Obsidian CLI for DOM QA, and a natively multimodal model. MinerU, OpenSSL, Keychain, and token state are required only for `--extraction mineru`.

## Core workflow

1. Run `scripts/preflight.py` and ask its questions in stages. Resolve the course through the persistent registry. Read [references/course-routing.md](references/course-routing.md).
2. Confirm the extraction mode, the note granularity, and the conversion profile. Read [references/document-profiles.md](references/document-profiles.md).
3. Derive one self-contained output folder per document from the matched semester, course, and document slug. Keep every source PDF/PPT/DOC/XLS outside the vault.
4. Read the source **natively**, page by page, before writing anything. Drop furniture, find the document's own section outline, and note which pages carry real content.
5. Work in a uniquely named system temporary directory, falling back to a non-hidden `tmp/` directory inside the installed skill.
6. Run `scripts/plan-note-structure.py` to draft `note-plan.json` and `page-ledger.json`, then correct them against what you actually saw. Set `draft: false` on both.
7. Write the note or notes. Apply [references/obsidian-style.md](references/obsidian-style.md) and [references/output-contract.md](references/output-contract.md).
8. Extract only the visuals whose structure matters and name them semantically. See [references/asset-naming.md](references/asset-naming.md).
9. Optional deterministic LaTeX normalization: run `obsidian-latex-refiner` when enabled; it handles marker-free notes as a single segment.
10. Read each note and allocate one isolated staging/output tuple per Canvas. Run `scripts/plan-canvas-batch.py`. With one note, direct execution or one subagent is allowed; with two or more, create one subagent task per note.
11. Render temporary QA with `scripts/fill-report.py`, run [references/validation.md](references/validation.md), extract the facts needed for the final response, delete all QA state on success, then send the concise summary.

## Non-negotiable boundaries

- Do not claim that source-to-note conversion is lossless. Optimize for semantic fidelity with visual fallback.
- Do not dump the extraction result into the vault. The extraction is input, never the deliverable.
- Do not invent missing content or normalize an uncertain equation into a confident-looking result.
- Do not keep slide furniture: agendas, section dividers, course-admin pages, exercise pages, repeated chrome, page numbers, and decorative slides belong in the ledger as `dropped`, not in the note.
- Never decide note granularity silently. Ask the user on every conversion.
- Never run native conversion on a model that cannot see the source pages; re-run with `--extraction mineru` instead.
- Resolve every destination under the registered semester root. Reject absolute child paths, `..` traversal, or a resolved path that escapes the course folder.
- Do not copy, move, embed, or symlink source PDFs, presentations, office documents, or archives into the Obsidian vault.
- Do not create `.staging`, `.tmp`, `.cache`, backup directories, second Markdown versions, or any other dot-prefixed path in the vault.
- Keep runtime registry data under this installed skill's `state/` directory.
- When `--extraction mineru` is used, the API token may persist only as ciphertext at `state/mineru-api-token.enc.json`, passed only through the `MINERU_TOKEN` child-process environment. Never use CLI `--token`, `mineru-open-api auth`, verbose HTTP logging, or direct MinerU HTTP calls.
- Do not fall back to a local PDF parser, a local MinerU runtime, a similarly named skill, or the unauthenticated lightweight API.

## Supporting resources

- [references/requirements.md](references/requirements.md) — prerequisites and the native-versus-MinerU capability split.
- [references/workflow.md](references/workflow.md) — the staged pipeline.
- [references/document-profiles.md](references/document-profiles.md) — what each profile must produce.
- [references/output-contract.md](references/output-contract.md) — folders, notes, assets, plan and ledger.
- [references/obsidian-style.md](references/obsidian-style.md) — note anatomy and Obsidian syntax.
- [references/asset-naming.md](references/asset-naming.md) — semantic asset names.
- [references/quality-gates.md](references/quality-gates.md) — completion gates.
- [references/validation.md](references/validation.md) — the validator invocation and checks.
- [references/mineru-cli.md](references/mineru-cli.md) and [references/mineru-normalization.md](references/mineru-normalization.md) — only when `--extraction mineru`.
- [references/course-routing.md](references/course-routing.md) — registering and matching course folders.
- [references/canvas-batch-delegation.md](references/canvas-batch-delegation.md) — one subagent per note.
- [../obsidian-canvas-designer/SKILL.md](../obsidian-canvas-designer/SKILL.md) — delegated Canvas design.
- [../obsidian-latex-refiner/SKILL.md](../obsidian-latex-refiner/SKILL.md) — optional deterministic math normalization.
- [../slide-layout-refiner/SKILL.md](../slide-layout-refiner/SKILL.md) — only for MinerU-mode transcription.
