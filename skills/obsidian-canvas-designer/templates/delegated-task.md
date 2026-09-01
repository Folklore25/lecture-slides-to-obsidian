Use `$obsidian-canvas-designer` to complete a Canvas-only task.

Inputs:

- vault root: `<absolute-vault-root>`
- complete note: `<absolute-note-path>`
- conversion profile: `<lecture-notes|policy-document|paper>`
- final Canvas: `<absolute-canvas-path>`
- staging directory: `<absolute-staging-path-outside-vault>`
- assets directory: `<absolute-document-assets-path>`
- overwrite authorized: `<true|false>`
- phase: `<FULL|AUTHORING|RENDER>`

Do not invoke extraction, MinerU, credentials, course routing, Markdown reconstruction, or conversion reports. Do not edit the complete note.

For `FULL`, run the entire workflow. For `AUTHORING`, run note inspection/recall-skeleton, semantic authoring, first build, and aesthetic QA, then return `READY_FOR_RENDER` without opening the real renderer. For `RENDER`, continue the existing task after the orchestrator grants the exclusive renderer slot; measure/reflow, rerun aesthetic QA, and pass the final renderer check.

If exact H2 anchors are missing, return their H3 candidates and stop without modifying the note.

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
