# Canvas concurrency and delegation

Canvas work is **lease-guarded, not forbidden to run concurrently**. The reason the lane used to be limited to one agent was a spurious focus requirement, not a real resource limit; that is fixed. What remains real is that the DOM step drives a single shared Obsidian application.

## What is parallel and what is not

| Stage | Shared resource | Concurrency |
| --- | --- | --- |
| Recall model authoring | none (files) | unbounded |
| First Canvas build | none (files) | unbounded |
| Static aesthetic QA | none (files) | unbounded |
| DOM measure / reflow / final check | the Obsidian app | one at a time, queued by `obsidian-gui-lock.py` |

The DOM step takes 2–3 seconds per Canvas. Everything else is file work. So parallelising Canvas work across agents is both safe and cheap: they queue only for the measurement.

## The lease

`scripts/canvas-render-qa.py` takes the lease itself; agents do not coordinate by hand. To inspect or drive it directly:

```text
skills/obsidian-canvas-designer/scripts/obsidian-gui-lock.py status  --vault-root <vault>
skills/obsidian-canvas-designer/scripts/obsidian-gui-lock.py acquire --vault-root <vault> --owner <agent-label> --timeout 120
skills/obsidian-canvas-designer/scripts/obsidian-gui-lock.py release --vault-root <vault> --owner <agent-label>
```

- Keyed by vault path, so separate vaults never block each other.
- A lease whose holder pid is gone is reclaimed automatically, so a crashed agent cannot wedge the lane.
- Re-entrant for the same owner, so a nested call cannot deadlock.
- Give every agent a distinct `--owner` label so a timeout message names the blocker.

## Rules

- Never activate the Obsidian application. Do not call `open -a Obsidian`, do not raise its window, and do not add a foreground requirement to a render profile.
- Never measure two Canvases at once outside the lease. The lease is the only sanctioned way to serialize the DOM step.
- Per-Canvas isolation stays mandatory: one note, one recall model, one Canvas path, one assets directory, one staging directory. Validate it and get a suggested order with `scripts/plan-canvas-batch.py --manifest <batch.json> --output <staging>/canvas-batch-plan.json`.
- Layout, hierarchy, colour, edge routing, and QA discipline belong to `obsidian-canvas-designer`. Driving that skill is not the same as hand-authoring Canvas JSON, and a returned Canvas must never be restyled by the caller.

## Process and cleanup

1. Prepare as many Canvases in parallel as capacity allows.
2. Let the measurement queue on the lease.
3. Validate each Canvas independently with the package validator.
4. Report one row per note: Canvas, aesthetic score, DOM status, review items, cleanup state. Never collapse a partial batch into a single PASS.
5. Delete each staging directory only after its Canvas passes final validation.
