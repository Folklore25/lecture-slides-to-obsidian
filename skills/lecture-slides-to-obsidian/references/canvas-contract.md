# Relationship canvas contract

Reference implementation: <https://github.com/heleninsights-dot/phd-deepread-workflow/tree/main>

Adapt its central-document, critical-thinking-node, directed-edge, and verifier pattern. Do not copy its local PDF extraction or fixed paper-only 9-node layout.

## Required artifact

Create `<document-slug>.canvas` beside `<document-slug>.md`. Use [../templates/relationship.canvas](../templates/relationship.canvas) as a layout seed, then replace placeholders with evidence from the complete Markdown and structured MinerU blocks.

## Node model

- One central `file` node points to `<document-slug>.md`.
- Section `file` nodes point to the same Markdown with `subpath` values such as `#Learning objectives` or `#Methods`.
- Asset `file` nodes point only to files under `assets/`.
- `text` nodes contain concise concepts, questions, comparisons, rules, or critiques derived from the source.
- Optional `group` nodes organize dense canvases, with child nodes positioned inside their bounds.
- Never create file/link nodes for the original PDF/PPT/office file or its absolute path.

Profile-specific relationships:

- `lecture-notes`: objectives → concepts → examples/evidence → questions/connections.
- `policy-document`: scope → actors → obligations → exceptions → enforcement → cross-references.
- `paper`: research question → argument → evidence/methods → assumptions/limitations → alternatives/open questions.

Create only relationships supported by the source. Typical edge labels are `defines`, `explains`, `depends on`, `supports`, `contrasts with`, `example of`, `exception to`, and `raises`.

## JSON Canvas rules

- Top-level object contains `nodes` and `edges` arrays.
- Every node and edge ID is a unique 16-character lowercase hexadecimal string.
- Every node has `id`, `type`, `x`, `y`, `width`, and `height`.
- File nodes have `file`; text nodes have `text`; group nodes may have `label`.
- Every edge references existing node IDs through `fromNode` and `toNode`.
- Side values are `top`, `right`, `bottom`, or `left`; end values are `none` or `arrow`.
- Keep 50–100 px spacing, avoid overlaps, and use a readable left-to-right or hub-and-spoke flow.
- File paths are vault-relative and resolve inside the document folder.

## Validation

Parse the JSON, verify unique IDs, references, types, required fields, path containment, source-original exclusion, and basic non-overlap. Canvas creation is not complete until `scripts/validate-output.py` passes.
