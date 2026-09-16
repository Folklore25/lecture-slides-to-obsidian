# Synthetic fixtures

Only reproducible, self-authored, redistributable fixtures belong here. Add the generator source, a short purpose statement, and the matching case manifest entry with each PDF.

A fixture folder that represents a *document folder* must contain nothing but the delivered artifacts: Markdown notes, their `.canvas` files, and `assets/`. Validation globs top-level `*.md`, so fixture documentation belongs in this directory, not inside the fixture.

## `valid-document-folder`

Exercises the MinerU transcription contract: one note with `<!-- source-page: N -->` markers, `page-PPP-kind-NN.ext` assets, and a marker-based recall model. Hand-authored; `content-list-v2-policy.json` drives the reconstruction test.

## `section-notes-folder`

Exercises the content-driven contract: one note whose H2 headings equal the sections declared in `../staging/note-plan.json`, no page markers, a semantic asset name, one Canvas, and the matching `../staging/page-ledger.json` plus `../staging/page-groups.json`.

The note, plan, ledger, and page groups are hand-authored. The Canvas and the placeholder PNG are derived, so regenerate them with:

```bash
python3 tests/fixtures/synthetic/generate-section-notes-folder.py
```

The generator builds the Canvas with the real `obsidian-canvas-designer` renderer from `templates/recall-model.content-driven.example.json`, then rewrites the vault-relative file nodes to document-relative ones so the fixture validates under `--fixture-mode`. Nothing here contains course material, student data, or credentials.
