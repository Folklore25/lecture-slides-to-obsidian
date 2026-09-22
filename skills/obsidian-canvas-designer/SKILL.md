---
name: obsidian-canvas-designer
description: Design, render, and verify high-readability Obsidian knowledge Canvases from complete Markdown notes and semantic models. Use directly when only Canvas is missing, or as a delegated drawing subskill; do not start document extraction, course routing, or note conversion.
metadata:
  required-skills: "json-canvas, obsidian-cli"
  design-reference: "axtonliu/axton-obsidian-visual-skills@obsidian-canvas-creator"
---

# Obsidian Canvas Designer

Turn an evidence-backed semantic model into a scannable Obsidian Canvas that remains readable in the supported local renderer. This skill owns Canvas information density, layout, hierarchy, color, edge routing, DOM sizing, and final Canvas QA.

## Operation boundary

This is the `canvas-only` entry point. If complete Markdown already exists, do not load extraction, MinerU, token storage, course routing, conversion reports, or the parent workflow. Canvas work begins with note inspection and ends with Canvas/aesthetic/render artifacts.

## Required inputs

- one complete Markdown note inside the vault, per task;
- staging recall-model JSON following [references/recall-model.md](references/recall-model.md);
- vault root and final Canvas path;
- optional document-local `assets/` containing only derived visuals.

When a document produced several notes, each note gets its own task, its own Canvas, and its own staging paths. Never combine two notes in one subagent.

If delegated by another Agent, follow [references/delegation-contract.md](references/delegation-contract.md). Do not re-interpret course routing, extraction-mode, or profile decisions.

A vault root must be supplied explicitly. Do not discover it with `obsidian vault info=path`: an explicit root is deterministic and keeps this step independent of the app. If the caller did not supply one, ask for it. Never infer the root from an arbitrary ancestor folder and never fall back to a bare filename.

## Workflow

1. Explicitly load `json-canvas`. Load `obsidian-cli` only to understand the DOM commands; **never call `obsidian` yourself.** The single permitted caller is `scripts/canvas-render-qa.py`.
2. Run `scripts/recall-skeleton.py` before semantic authoring. It inventories exact H2 anchors, H3 review candidates, coverage rows, and whether the note carries page provenance. `concept.source_heading` may reference only a real `## H2`; never promote or edit the user's headings inside this skill.
3. Read the complete note and fill the recall-model draft. Reject unsupported relationships. Omit `source_page` for a note without page markers; require it, and the matching heading/page pair, when markers are present.
4. Read [references/axton-aesthetics.md](references/axton-aesthetics.md) and choose a layout pattern from the semantic graph, not from source section order.
5. Keep every concept card atomic and scannable: H3 title, one short statement, at most two details, and one compact source link. Put recall questions in the shared active-recall zone instead of repeating them in every card.
6. Run `scripts/build-canvas.py` for the first layout.
7. Run `scripts/canvas-aesthetic-qa.py`; revise until its hard gates pass and score is at least 85. Run it again after DOM-driven reflow and return only the final SHA-bound aesthetic check.
8. Run `scripts/canvas-render-qa.py measure`, rebuild with `--render-metrics`, and run `check` against the real local Obsidian DOM. The DOM step takes the shared GUI lease itself, so several agents may prepare Canvases concurrently and only the measurement queues. Never activate the Obsidian window or require it to be frontmost. Do not use screenshots as the default gate.
9. Delegated work returns the Canvas plus staging aesthetic/measurement/check JSON files without deleting them; the orchestrator owns package validation and cleanup. Standalone Canvas-only work reports the same PASS evidence, then deletes its temporary authoring/QA files unless the user asks to preserve them.

## Non-negotiable visual rules

- Use one dominant reading direction. Avoid hub-and-spoke unless the content is genuinely radial.
- Reserve 120–180 px between groups when an edge label occupies that channel; reserve 60–90 px between vertically stacked cards.
- Treat the purple overview and red source-note preview as one top orientation lane. Compute the learning-module `y` from the rendered bottom of that lane plus 80 px; never use a fixed module `y`. Recompute it after DOM-driven height changes.
- Limit the visible palette to semantic roles. Avoid assigning a new color merely because a group is next in sequence.
- Keep edge labels active and short. Minimize crossings and reject edges that pass through unrelated cards.
- At fit-all zoom, judge only structure. At the supported reading zoom, body text must meet the local sidebar reference and every card must retain the measured height margin.
- Card height is a two-sided contract: after subtracting the local `34px` renderer chrome, effective headroom must be `8–12px`. Do not accept cards with large empty tails simply because they are not clipped.
- Do not call `open -a Obsidian`, do not raise the Obsidian window, and do not add a foreground requirement to a render profile. Concurrency is handled by the shared GUI lease, not by demanding the user's screen.
- Do not add or use an offline-estimate completion flag. If the supported Obsidian renderer is unavailable, return FAIL with the first-pass Canvas unaccepted.
- Never replace the complete Markdown with Canvas prose. The Canvas is a retrieval map with compact links back to detail.

## Resources

- Read [references/canvas-contract.md](references/canvas-contract.md) for the artifact contract.
- Read [references/recall-model.md](references/recall-model.md) before accepting semantic input.
- Read [references/asset-contract.md](references/asset-contract.md) before selecting visuals.
- Read [references/axton-aesthetics.md](references/axton-aesthetics.md) before layout or visual revision.
- Read [references/render-qa.md](references/render-qa.md) before final acceptance.
- Orchestrators may instantiate [templates/delegated-task.md](templates/delegated-task.md) for parallel Canvas-only subagents; do not build a runtime-specific batch launcher into this skill.
- [templates/recall-model.lecture-notes.example.json](templates/recall-model.lecture-notes.example.json) shows the marker-based shape; [templates/recall-model.content-driven.example.json](templates/recall-model.content-driven.example.json) shows the marker-free shape.
