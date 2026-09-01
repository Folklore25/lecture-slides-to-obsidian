# Knowledge-recall Canvas contract

The Canvas is a **retrieval map**, not a table of contents and not a second copy of the Markdown. After reading the full material, a learner should be able to look at the Canvas for about one minute and recover:

1. the central question and answer;
2. the major learning modules;
3. the dependency, causal, contrast, evidence, and application links between ideas;
4. the shortest logic chain that reconstructs the lesson;
5. important boundaries or common confusions;
6. several prompts that test active recall;
7. confirmed additions from class when running in `post-class` mode.

The complete Markdown remains the source of detail. Every concept node links back to a real Markdown heading. Do not copy paragraphs into the Canvas.

Reference inspiration: [phd-deepread-workflow](https://github.com/heleninsights-dot/phd-deepread-workflow/tree/main). Retain its useful critical-thinking pattern—argument, assumptions, evidence, limitations, alternatives, questions—but do not copy its fixed paper-only layout or placeholder nodes.

## Required two-stage generation

Do not ask `build-canvas.py` to infer meaning from Markdown headings. The delegating Agent must first read the **complete note**, reason about the content, and write a staging `recall-model.json` following [recall-model.md](recall-model.md). Then run:

```text
scripts/build-canvas.py \
  --note <document.md> \
  --vault-root <vault-root> \
  --profile <profile> \
  --model <staging/recall-model.json> \
  --output <document.canvas>
```

The model is temporary Agent QA state. Delete it together with the conversion report after successful Canvas/output validation. Keep it only while debugging a failed build.

## Information architecture

The renderer creates four visual zones:

- **One-minute recall:** central question, one-sentence answer, and three to five takeaways.
- **Learning modules:** two to seven left-to-right groups. Group by conceptual function, not slide/page order.
- **Concept network:** four to twenty atomic nodes, normally eight to sixteen. Each node states one idea, gives at most three details, includes a recall cue, and links to its full source section.
- **Synthesis strip:** logic chain, distinctions/boundaries, and active-recall prompts; post-class additions appear here.

The Canvas may omit low-value detail from view, but not silently. The model's `coverage` ledger must account for every H2 heading/page occurrence by mapping it to concept nodes or giving a concrete omission reason. This is how repeated headings stay distinct and the Canvas remains concise without pretending to contain the full note.

## Relationship quality

Relations must say what one concept does to another. Use a small supported vocabulary:

`requires`, `causes`, `enables`, `explains`, `supports`, `contrasts`, `limits`, `example-of`, `part-of`, `leads-to`, `qualifies`, `applies-to`.

Write a short active edge label such as `provides the comparison baseline`, `fails when latency dominates`, or `turns observations into a decision`. Never use `related to`, `contains section`, `followed by`, `next`, or similar labels that only describe document structure.

Every relation records a short `why` in the staging model. It must be supported by the source, by explicit in-class notes, or by a conservative synthesis of both. The final concept graph must be connected, but selective: use between `N-1` and `2N` concept relations and keep each concept at six connections or fewer.

## Visual selection

Do not attach every extracted image to the main note node. Select at most six memory-critical visuals—only diagrams, tables, equations, or charts whose absence would make an important concept harder to reconstruct. Each selected visual is attached to the concept it explains. Paths follow [asset-contract.md](asset-contract.md).

## Pre-class and post-class lifecycle

- `pre-class`: build from the complete converted material. Leave `in_class_additions` empty; never invent what a lecturer might say.
- `post-class`: re-read the complete Markdown including the learner's `## In-class notes`, rebuild the semantic model, and put only confirmed additions, corrections, exam cues, or lecturer emphasis in `in_class_additions`.

Do not silently overwrite a Canvas that may contain manual edits. `build-canvas.py` refuses an existing output unless `--overwrite` is explicitly supplied after preserving or reconciling those edits.

For first creation, the Canvas path does not exist and `--overwrite` must be omitted. The DOM-driven second pass overwrites the first-pass Canvas created in the same run, so it uses `--render-metrics ... --overwrite`. A later refresh of a possibly user-edited Canvas requires an explicit reconciliation/overwrite decision.

## Readability acceptance tests

A finished Canvas must pass all of these:

- **Orientation test:** at fit-to-screen, only the overview, module order, and synthesis strip need to be distinguishable; body text is not judged at this zoom.
- **Reading-scale test:** at the supported `zoom = 0`, the effective Canvas font is `16px`, at least as large as the local `13px` sidebar text.
- **One-minute test:** at reading scale, the overview plus logic chain recovers the lesson's thesis without opening the Markdown.
- **Why-edge test:** every arrow can be read as a meaningful sentence, `A <label> B`.
- **Coverage test:** every major Markdown section is mapped or explicitly excluded in staging.
- **Traceability test:** every concept links to an exact existing `## H2` and states its 1-based source page; H3 is not accepted and selected assets resolve inside the document folder.
- **Density test:** no placeholder nodes, paragraph dumps, isolated concepts, node overlaps, or hub with more than six semantic connections.
- **Aesthetic test:** [axton-aesthetics.md](axton-aesthetics.md) and `canvas-aesthetic-qa.py` pass before DOM measurement.
- **Renderer test:** [render-qa.md](render-qa.md) reports every text node above its measured height plus safety margin; screenshots do not count as this evidence.

## JSON Canvas invariants

- Create `<document-slug>.canvas` beside `<document-slug>.md`.
- Use unique 16-character lowercase hexadecimal IDs.
- File paths are relative to the vault root, never relative to the Canvas.
- Never create a file/link node for the original PDF/PPT/Office source or its absolute path.
- Keep 50–100 px spacing and let groups sit behind their child nodes.
- Treat offline `text_height()` as an initial estimate only. Rebuild from Obsidian DOM measurements before final validation.
- Production delivery never skips renderer QA. Offline estimates are allowed only in synthetic/unit fixtures and must not be reported as a completed Canvas.
- Standalone Canvas-only work finishes with `canvas-aesthetic-qa.py` and `canvas-render-qa.py check`. When delegated by the course skill, return those SHA-bound artifacts to its sibling `scripts/validate-output.py`; fixture-relative paths are test-only.
