# Multi-file conversion dispatch

## Trigger

Count the distinct source files in the request after routing and before any extraction:

- `N = 0`: nothing to convert.
- `N = 1`: convert directly in the main Agent.
- `N >= 2`: **dispatch is mandatory.** Announce the split and start one subagent task per file. Do not ask for extra permission when the user already asked for those files.

## What the main Agent keeps

Shared state is resolved **once, before dispatch**, by the main Agent. Parallel workers must never race on it:

- course routing, semester resolution, and the course registry;
- the `Lectures/<document-slug>` layout and slug-collision decisions;
- encrypted MinerU token state and the Keychain wrapping key;
- the Canvas lane.

## What each subagent receives

One source file, one document folder, one staging directory, one conversion profile, and the canvas-batch manifest entry for the files it must not touch. Nothing else.

Each subagent returns:

- the note or notes;
- `note-plan.json` and `page-ledger.json`;
- the extracted `assets/`;
- package-validation evidence for its own document folder.

**A conversion subagent must not build, measure, or check a Canvas.** Canvas is the main Agent's serial lane; see [canvas-batch-delegation.md](canvas-batch-delegation.md).

## Planning and isolation

```text
scripts/plan-conversion-batch.py --manifest <batch.json> --max-parallel <slots> \
  --vault-root <vault-root> --output <staging>/conversion-batch-plan.json
```

The manifest shape is in [../templates/conversion-batch-manifest.example.json](../templates/conversion-batch-manifest.example.json).

The planner rejects a batch that would let two workers collide. It fails on a duplicate id, a duplicate source path, a duplicate document folder, a duplicate staging directory, an unsupported profile, a source inside the vault, a document folder outside the vault, or a staging directory inside the vault.

One staging directory per file. Never share note, plan, ledger, or asset paths between tasks. The planner emits `parallelism` and `waves`; a capacity of one still means one subagent task per file, just in sequential waves.

## Canvas

A per-file subagent may produce its own note and its own Canvas; the file split and the Canvas split are the same split. Canvas authoring parallelises with everything else, and only the DOM step is serialized by the shared GUI lease, which `canvas-render-qa.py` takes itself. See [canvas-batch-delegation.md](canvas-batch-delegation.md).

## Failure behavior

- Report one status row per file. One failed file does not invalidate unrelated files.
- Retry only the failed file and keep its isolated staging evidence.
- Do not merge two files into one document folder to "save" a task.

## If subagents are unavailable

Report that the mandatory multi-file dispatch is unavailable, and say which files were not converted. Do not silently convert the whole batch in the main Agent, and do not drop files to make the batch fit.
