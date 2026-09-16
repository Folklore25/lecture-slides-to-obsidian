# Canvas lane

Canvas is a **single exclusive lane**: exactly one Canvas is built, measured, and checked at a time, and the main Agent owns the lane.

## Why it is serial

Canvas QA drives the local Obsidian application through `canvas-render-qa.py` — DOM measurement, measured rebuild/reflow, and the final render check. The Obsidian app is single-instance shared state. Two Canvas tasks in flight at once fight over it, and the measured heights stop meaning anything. This is a hard resource constraint, not a tuning knob.

## Rules

- **Parallelism is always 1**, for one note or twenty. There is no parallel-safe authoring phase either: a Canvas task that is only "authoring" still holds the recall model, the Canvas path, and the designer skill state for that note, and the lane must stay clear.
- **The main Agent runs the lane.** It loads `obsidian-canvas-designer` and drives it one Canvas at a time. Handing a Canvas to a helper is allowed only one at a time — never two concurrently, and never a fan-out.
- **Never run `canvas-render-qa.py` concurrently with any other Canvas work.**
- **Per-Canvas isolation is still mandatory:** one note, one recall model, one Canvas path, one assets directory, one staging directory. Validate it and get the serial order with:

```text
scripts/plan-canvas-batch.py --manifest <batch.json> --output <staging>/canvas-batch-plan.json
```

That planner validates isolation and emits `canvas_lane.order`. It creates no agents and no fan-out.

## Who owns the drawing

Layout, hierarchy, colour, edge routing, DOM sizing, and Canvas QA belong to `obsidian-canvas-designer`. The main Agent drives that skill; it does not hand-author Canvas JSON, and it must not redraw or restyle a returned Canvas. The semantic recall model is authored from the complete note, one note per Canvas.

## Process order and cleanup

1. Take the next id from `canvas_lane.order`.
2. Build the recall model from that complete note.
3. Build, measure, reflow, and run the final aesthetic and DOM checks for that Canvas.
4. Validate it with the package validator and record the result.
5. Release the lane, then start the next Canvas.

Delete each staging directory only after that Canvas passes final package validation and its result has been summarized. Delete the batch manifest and batch plan once every Canvas has a terminal PASS/FAIL row.

## Completion summary

Report one row per note: Canvas path, aesthetic score, DOM status, review items, and cleanup state. Never collapse a partial batch into a single unqualified PASS.
