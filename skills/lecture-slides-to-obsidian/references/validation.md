# Output validation

Run this before declaring completion.

## Content-driven notes (native, or MinerU as an aid)

```text
scripts/validate-output.py <document-folder> --vault-root <vault-root> \
  --plan <run>/note-plan.json --ledger <run>/page-ledger.json \
  --report <run>/conversion-report.md \
  --recall-model <run>/recall-model.json \
  --aesthetic-check <run>/canvas-aesthetic-check.json \
  --render-metrics <run>/canvas-render-metrics.json \
  --render-check <run>/canvas-render-check.json \
  --delete-qa-on-success
```

Add `--page-groups <run>/<stem>.content-list-v2.compat.json` when MinerU ran; that upgrades conservation from evidence-only to evidence plus per-page text recall. Add `--allow-heavy-drop` only after confirming the source really is mostly furniture.

`--plan` and `--ledger` are mandatory whenever a note carries no page markers. That is the normal case for native reading.

## MinerU transcription (page markers in force)

```text
scripts/validate-output.py <document-folder> --vault-root <vault-root> \
  --report <run>/conversion-report.md --recall-model <run>/recall-model.json \
  --latex-refinement-report <run>/latex-refinement-report.json \
  --aesthetic-check <run>/canvas-aesthetic-check.json \
  --render-metrics <run>/canvas-render-metrics.json \
  --render-check <run>/canvas-render-check.json --delete-qa-on-success
```

When the LaTeX refinement report is supplied it must form a single snapshot-to-refined chain whose final hash equals the delivered Markdown.

## Folder checks

- At least one primary Markdown file, one Canvas per note, and `assets/` exist.
- `conversion-report.md` does not exist in the document folder or anywhere inside the vault.
- No PDF, PPT/PPTX, DOC/DOCX, XLS/XLSX, ZIP, or other source original exists anywhere in the document folder.
- All derived paths remain inside the document folder.
- No dot-prefixed file or directory exists in the document folder.

## Note checks

- UTF-8 text with closed YAML frontmatter carrying the required properties.
- Exactly one H1 per note.
- H2 headings equal the planned section headings, with no duplicates.
- Marks: content-driven notes contain no `<!-- source-page: N -->`; MinerU transcription notes contain monotonic in-range markers.
- Every Markdown asset link and Obsidian embed resolves.
- Every wikilink resolves inside the vault when `--vault-root` is supplied.
- Content-driven assets use lowercase semantic kebab-case names; MinerU transcription assets use flat `page-PPP-kind-NN.ext` with contiguous per-page sequences.
- Content-driven assets are referenced by a note or a Canvas file node.

## Ledger and conservation checks

- The plan and ledger are final (`draft: false`) and internally consistent.
- Every source page is present exactly once with a supported disposition.
- Dropped pages carry a controlled reason; a heavy drop needs explicit approval.
- Every kept or merged page maps to a planned note and section and carries an `evidence` phrase that occurs in that note.
- With `--page-groups`, per-page text recall must clear `--conservation-threshold` (default `0.35`) unless the ledger declares `recall_exempt` with a reason. The validator reports the measured recall per page either way.

## Canvas checks

- Valid JSON with `nodes` and `edges` arrays.
- All node and edge IDs are unique 16-character lowercase hex strings.
- Node types and required fields are valid, and every edge endpoint resolves.
- Exactly one overview, logic-chain synthesis, distinctions, and active-recall node exists.
- 2–7 learning-module groups and 4–20 concept nodes.
- Concept cards use compact H3 hierarchy and link to an exact `## H2` in the paired note. Include `Source p.N` only when the note actually carries page provenance.
- Semantic concept edges form one connected graph, stay between `N-1` and `2N`, avoid generic labels, and keep every concept at six connections or fewer.
- Final Obsidian DOM check matches the delivered Canvas hash and reports no node below its measured safety height.
- File-node paths resolve inside the document folder and never target a source original.

## Temporary QA checks

- All fixed report sections exist and inventory rows are numeric, including zeros.
- Structural alignment and pixel-level visual comparison remain separate gates; unperformed rendering is `NOT-CHECKED`, never `PASS`.
- No token, Authorization header, signed URL, or absolute source path appears.
- `recall-model.json` is outside the vault, valid JSON with schema version 1, and was used to build the Canvas.
- `--delete-qa-on-success` removes the report, recall models, plan, ledger, page groups, optional refinement reports, aesthetic checks, render metrics, and render checks before the final response is sent.

## Reporting

The validator returns non-zero when deterministic checks fail and preserves the report and plan/ledger for debugging. Do not reinterpret a failure as a warning.
