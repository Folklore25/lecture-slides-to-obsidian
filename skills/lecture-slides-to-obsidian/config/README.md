# Configuration contract

This directory contains the main conversion/routing contract.

- `pipeline.example.yaml` documents shared conversion and classification behavior.
- Canvas layout and renderer configuration belong to the sibling `obsidian-canvas-designer` skill.
- `../state/course-registry.example.yaml` documents the persistent, local-only mapping from course names to semester/course destinations.

Rules for future changes:

- Keep safe defaults: preserve the source, refuse overwrite, and retain visual fallback.
- Add a schema version before changing field meaning.
- Document new fields here and cover them with contract tests.
- Keep backend-specific options under a backend namespace rather than leaking them into the shared output contract.
- Store the real course registry at `../state/course-registry.yaml` relative to this directory.
- Never place API keys, Canvas cookies, access tokens, real vault paths, or personal course metadata in committed configuration.
