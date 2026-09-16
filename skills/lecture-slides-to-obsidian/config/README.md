# Configuration contract

This directory contains the main conversion, extraction, and routing contract.

- `pipeline.example.yaml` documents shared conversion, extraction-mode, note-planning, and classification behavior.
- Canvas layout and renderer configuration belong to the sibling `obsidian-canvas-designer` skill.
- `../state/course-registry.example.yaml` documents the persistent, local-only mapping from course names to semester/course destinations.

Rules for future changes:

- Keep safe defaults: preserve the source, refuse overwrite, and retain visual fallback.
- Keep `extraction.mode: "native"` as the default. MinerU is an opt-in aid, never a prerequisite.
- Keep `note_planning.granularity` as `ask-user-every-time`. Never introduce a silent default.
- Add a schema version before changing field meaning.
- Document new fields here and cover them with contract tests.
- Keep backend-specific options under a backend namespace rather than leaking them into the shared output contract.
- Store the real course registry at `../state/course-registry.yaml` relative to this directory.
- Never place API keys, Canvas cookies, access tokens, real vault paths, or personal course metadata in committed configuration.
