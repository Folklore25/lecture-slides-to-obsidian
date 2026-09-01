# Multi-file Canvas delegation

The main Agent owns batch coordination. The Canvas designer subagents own exactly one document each.

## Trigger

Count unique Canvas work items after routing and before drawing:

- `N = 0`: no Canvas delegation.
- `N = 1`: direct `obsidian-canvas-designer` execution or one subagent is allowed.
- `N >= 2`: subagent delegation is mandatory. Announce that each file will receive an isolated Canvas task; do not ask for additional permission when delegation remains inside the user's requested files.

Run `scripts/plan-canvas-batch.py --manifest <batch.json> --max-parallel <available-slots> --output <staging>/canvas-batch-plan.json`. The planner records the mandatory task split and waves; it does not create agents by itself. With `--output`, stdout stays compact and the full per-file task list remains in staging.

Use the current environment's native subagent/task mechanism. If it cannot create subagents, report that the mandatory multi-file Canvas contract is unavailable; do not silently draw the entire batch in the main Agent. A capacity of one still uses separate subagent tasks in sequential waves.

## One item per subagent

Each task receives only:

- one complete note;
- one recall-model/staging directory;
- one Canvas output path;
- that document's assets directory;
- vault root, profile, and overwrite decision;
- the Canvas designer's delegated-task template.

Never send several notes to one Canvas subagent. Never share recall-model, Canvas, aesthetic, metric, or render-check paths between tasks.

## Two-phase coordination

### Phase A — parallel-safe

Start one task per document, up to the environment's subagent limit. Queue remaining tasks in later waves without merging them. Each subagent performs:

1. H2/page inspection and recall skeleton;
2. semantic model authoring;
3. first Canvas build;
4. aesthetic QA and revisions.

It then returns `READY_FOR_RENDER` with its file paths and aesthetic result. It must not call real DOM QA yet.

### Phase B — exclusive renderer lane

The local Obsidian app is shared state. Grant a renderer slot to only one Canvas subagent at a time. Send that existing subagent a follow-up to perform:

1. DOM measure;
2. measured rebuild/reflow;
3. final aesthetic check;
4. final DOM check;
5. SHA-bound PASS/FAIL return.

Wait for release before granting the slot to the next item. Do not run `canvas-render-qa.py` concurrently across subagents.

## Collection and failure behavior

- Validate every returned Canvas independently with the parent package validator.
- One failed item does not invalidate unrelated PASS items; report per-file status.
- Retry only the same document task and preserve its isolated staging evidence.
- The main Agent must not redraw or cosmetically edit a returned Canvas. Send revisions back to its owning subagent.
- Delete each staging directory only after that file passes final package validation and its result has been summarized.
- Delete the batch manifest and batch plan after every file reaches a terminal PASS/FAIL summary.

## Completion summary

Report one row per input file: note, Canvas, aesthetic score, DOM status, review items, and cleanup state. Do not collapse a partial batch into a single unqualified PASS.
