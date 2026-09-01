---
name: obsidian-canvas-designer
description: Design, render, and verify high-readability Obsidian knowledge Canvases from semantic models and complete notes. Use for delegated Canvas drawing or visual refinement; do not use for document extraction, course routing, or note conversion.
metadata:
  required-skills: "json-canvas, obsidian-cli"
  design-reference: "axtonliu/axton-obsidian-visual-skills@obsidian-canvas-creator"
---

# Obsidian Canvas Designer

Turn an evidence-backed semantic model into a scannable Obsidian Canvas that remains readable in the supported local renderer. This skill owns Canvas information density, layout, hierarchy, color, edge routing, DOM sizing, and final Canvas QA.

## Required inputs

- complete Markdown note inside the vault;
- staging recall-model JSON following [references/recall-model.md](references/recall-model.md);
- vault root and final Canvas path;
- optional document-local `assets/` containing only derived visuals.

If delegated by another Agent, follow [references/delegation-contract.md](references/delegation-contract.md). Do not re-interpret course routing or extraction decisions.

## Workflow

1. Explicitly load `json-canvas` and `obsidian-cli`.
2. Read the complete note and recall model. Reject unsupported relationships or missing heading/page provenance.
3. Read [references/axton-aesthetics.md](references/axton-aesthetics.md) and choose a layout pattern from the semantic graph, not from source section order.
4. Keep every concept card atomic and scannable: H3 title, one short statement, at most two details, and one compact source link. Put recall questions in the shared active-recall zone instead of repeating them in every card.
5. Run `scripts/build-canvas.py` for the first layout.
6. Run `scripts/canvas-aesthetic-qa.py`; revise until its hard gates pass and score is at least 85. Run it again after DOM-driven reflow and return only the final SHA-bound aesthetic check.
7. Run `scripts/canvas-render-qa.py measure`, rebuild with `--render-metrics`, and run `check` against the real local Obsidian DOM. Do not use screenshots as the default gate.
8. Return the Canvas plus staging aesthetic/measurement/check JSON files to the delegating Agent. Do not delete shared QA files; the orchestrator owns final package validation and cleanup.

## Non-negotiable visual rules

- Use one dominant reading direction. Avoid hub-and-spoke unless the content is genuinely radial.
- Reserve 120–180 px between groups when an edge label occupies that channel; reserve 60–90 px between vertically stacked cards.
- Limit the visible palette to semantic roles. Avoid assigning a new color merely because a group is next in sequence.
- Keep edge labels active and short. Minimize crossings and reject edges that pass through unrelated cards.
- At fit-all zoom, judge only structure. At the supported reading zoom, body text must meet the local sidebar reference and every card must retain the measured height margin.
- Never replace the complete Markdown with Canvas prose. The Canvas is a retrieval map with compact links back to detail.

## Resources

- Read [references/canvas-contract.md](references/canvas-contract.md) for the artifact contract.
- Read [references/recall-model.md](references/recall-model.md) before accepting semantic input.
- Read [references/axton-aesthetics.md](references/axton-aesthetics.md) before layout or visual revision.
- Read [references/render-qa.md](references/render-qa.md) before final acceptance.
