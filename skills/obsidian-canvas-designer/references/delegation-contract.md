# Delegation contract

The delegating Agent supplies:

- absolute vault root;
- absolute complete-note path inside that vault;
- absolute recall-model path under staging outside the vault;
- conversion profile;
- final `.canvas` path beside the note;
- optional document-local assets directory;
- staging paths for `canvas-aesthetic-check.json`, `canvas-render-metrics.json`, and `canvas-render-check.json`.

The Canvas subagent must not:

- ask the user to repeat course, semester, MinerU, language, OCR, or credential decisions;
- edit the complete Markdown, course registry, source original, token state, or unrelated vault files;
- promote H3 headings to H2, even when the note lacks usable anchors; report exact candidates instead;
- invent missing relationships to make the graph look fuller;
- overwrite an existing user-edited Canvas without an explicit overwrite instruction from the delegating Agent;
- delete shared staging QA files.

The subagent returns one concise object or message containing:

```text
canvas: <absolute path>
aesthetic_check: <absolute staging path>
render_metrics: <absolute staging path>
render_check: <absolute staging path>
status: PASS | FAIL
review_items: <empty or concrete list>
```

`PASS` requires the same Canvas SHA in the final render check, aesthetic score at least 85 with no hard failure, no clipped text, and the supported effective font size. On failure, return evidence and stop; do not downgrade a required gate to a warning.

Normal delegated production work preserves the Canvas and staging QA files for the orchestrator. An explicitly isolated forward test may instead inspect and report the same evidence, then delete its temporary vault/staging paths as instructed.
