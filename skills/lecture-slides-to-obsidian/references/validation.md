# Output validation

Run this before declaring completion:

```text
scripts/validate-output.py <document-folder> --vault-root <vault-root> --report <staging>/conversion-report.md --delete-report-on-success
```

## Folder checks

- Exactly one primary Markdown file, one relationship `.canvas`, and `assets/` exist.
- `conversion-report.md` does not exist in the document folder or anywhere inside the vault.
- No PDF, PPT/PPTX, DOC/DOCX, XLS/XLSX, ZIP, or other source original exists anywhere in the document folder.
- All derived paths remain inside the document folder.

## Markdown checks

- UTF-8 text with closed YAML frontmatter.
- Required properties from `output-contract.md` are present.
- Exactly one H1 exists.
- `source_pages` is a positive integer.
- Every `<!-- source-page: N -->` uses `1 <= N <= source_pages` and markers are monotonic.
- Every Markdown asset link and Obsidian embed resolves.
- Every visual asset is a flat `assets/page-PPP-kind-NN.ext` file; page numbers are valid and per-page/per-kind sequences are contiguous from `01`.
- When `--vault-root` is supplied, every non-heading wikilink resolves to a note or file within the vault.
- The profile is one of `lecture-notes`, `policy-document`, or `paper`.

Structured provenance must also be checked against MinerU content lists: marker N precedes page N's first included block. The standalone validator checks marker range/order, while the conversion pipeline records block-level evidence in the report.

## Canvas checks

- Valid JSON with `nodes` and `edges` arrays.
- All node and edge IDs are unique 16-character lowercase hex strings.
- Node types and required fields are valid.
- Every edge endpoint resolves.
- File-node paths resolve inside the document folder.
- No file or URL node targets a source-original format.
- Basic node rectangles do not overlap.

## Temporary report checks

- All fixed template sections exist.
- Content inventory includes figures, tables, equations, fallback pages, headers, footers, and footnotes, including zeros.
- Structural alignment and pixel-level visual comparison are separate gates.
- Unperformed visual rendering is marked `NOT-CHECKED`, not `PASS`.
- No token, Authorization header, signed URL, or absolute source path appears.
- After the Agent has extracted the facts needed for its final response, `--delete-report-on-success` removes the exact temporary report before that response is sent.

## Reporting

The validator returns non-zero when deterministic checks fail and preserves the report for debugging. Do not reinterpret a failure as a warning. Checks requiring MinerU block evidence or pixel rendering remain explicit temporary-report gates.
