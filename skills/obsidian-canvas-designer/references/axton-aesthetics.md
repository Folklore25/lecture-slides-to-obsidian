# Axton-informed Canvas aesthetics

Mandatory design reference: [Axton Liu's Obsidian Canvas Creator](https://github.com/axtonliu/axton-obsidian-visual-skills/tree/1265976d9746a84858b4b7b42fb86a215aa93de9/obsidian-canvas-creator), MIT licensed. This document adapts its useful layout, spacing, collision, visual-balance, and edge-crossing principles. It does not copy its character-count height estimates; local Obsidian DOM measurement is authoritative here.

## Choose the layout from the graph

- **Zoned left-to-right flow:** prerequisites, mechanisms, applications, boundaries. Default for lectures and policies.
- **Hierarchy/tree:** real parent-child decomposition with few cross-links.
- **Timeline:** chronology or sequential process where order is the main relationship.
- **Two-column/matrix:** comparison, before/after, alternatives, or independent dimensions.
- **Radial:** one genuine center with independent branches. Do not use it merely for visual novelty.
- **Circular:** feedback loops or recurring cycles only.

Mixed knowledge maps use a zoned layout with one dominant spine. Avoid force-directed placement for final output because it weakens stable reading order and deterministic diffs.

## Visual hierarchy

1. Overview is the only H1-scale object.
2. Group labels define major modules.
3. Concept cards use H3 titles, not H2.
4. Synthesis, distinctions, and active recall form one closing strip.
5. Asset nodes appear only beside the concept they materially explain.

The learner should identify overview → modules → concepts → synthesis before reading prose.

## Density budget

Each concept card contains:

- title no longer than 60 Latin characters or 30 CJK characters;
- one statement no longer than 180 characters;
- zero to two details, each no longer than 140 characters;
- one compact source link such as `Source p.14`.

Do not render the per-concept `recall_cue`; consolidate cues in the active-recall node. When a card exceeds this budget, split the concept or move detail back to Markdown.

## Spacing and rhythm

- Concept width: 440 px on the supported workstation.
- Inner group side padding: 40 px.
- Group header allowance: 90 px.
- Vertical card gap: 70 px.
- Inter-group edge-label channel: 160 px.
- Synthesis strip top gap: 180 px.
- Align coordinates and measured heights to a 10 px grid.

Repeat the same width and gap within one role. Variation should encode meaning, not compensate for accidental overflow.

## Color discipline

Use color semantically and sparingly:

- purple `6`: overview, synthesis, central claim;
- cyan `5`: mechanism, process, method;
- green `4`: evidence, example, application, finding;
- yellow `3`: foundation or neutral concept;
- orange `2`: rule, action, recall prompt;
- red `1`: boundary, exception, misconception, limitation.

Groups use the dominant semantic color of their contents, not a rotating rainbow sequence. A Canvas with more than five visible semantic colors needs explicit justification.

## Edges

- Keep labels to 2–5 words when possible.
- Connect from the nearest logical side.
- Prefer short orthogonal reading channels even though JSON Canvas stores only endpoints.
- Reorder cards within a group before adding more whitespace.
- Reject an edge whose centerline intersects an unrelated card.
- Minimize crossings; zero is the target, and more than `max(2, 10% of semantic edges)` is a hard failure.

## Balance and navigation

- Keep the overall bounding box near the workstation viewport aspect ratio when content permits.
- Avoid a single very tall group beside several short groups; redistribute or split the module.
- Fit-all view is an orientation map only. Final reading view is 1:1 and centered on the overview.
- The complete Canvas remains pannable; do not shrink all content to claim one-screen readability.

## Final review questions

- Is the reading order obvious without following every arrow?
- Does every color have one consistent meaning?
- Can any card lose a sentence without losing its retrieval value?
- Are long edges evidence of a bad position or a missing intermediate concept?
- Does the closing strip reconstruct the lesson without duplicating every card?
