Use `$obsidian-canvas-designer` to complete a Canvas-only task.

Inputs:

- vault root: `<absolute-vault-root>`
- complete note: `<absolute-note-path>`
- conversion profile: `<lecture-notes|policy-document|paper>`
- final Canvas: `<absolute-canvas-path>`
- staging directory: `<absolute-staging-path-outside-vault>`
- assets directory: `<absolute-document-assets-path>`
- overwrite authorized: `<true|false>`

Do not invoke extraction, MinerU, credentials, course routing, Markdown reconstruction, or conversion reports. Do not edit the complete note.

Run the note inspection/recall-skeleton step first. If exact H2 anchors are missing, return their H3 candidates and stop without modifying the note. Complete the semantic model, apply the required Axton-informed design rules, build the first Canvas, pass aesthetic QA, measure/reflow using the real Obsidian DOM, rerun aesthetic QA, and pass the final renderer check.

Return exactly:

```text
canvas: <path>
aesthetic_check: <path>
render_metrics: <path>
render_check: <path>
status: PASS | FAIL
review_items: <list>
```

Preserve staging artifacts for the orchestrator unless this is explicitly an isolated cleanup test.
