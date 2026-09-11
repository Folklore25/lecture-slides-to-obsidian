Use `$obsidian-latex-refiner` on this note. No vision model is required; the transform is content-conserving and source-agnostic.

Inputs:

- target Markdown: <absolute-note-path>
- run directory: <absolute-run-directory-outside-vault>

Steps:

1. Scan read-only: `python3 <skill-dir>/scripts/normalize-latex.py --target <target> --analyze --report <run-dir>/analysis.json`.
2. Read `recommended_transforms` and `review_items`; choose `--only` groups if a group is unsafe for this document.
3. Optionally preview: add `--dry-run`.
4. Apply: `python3 <skill-dir>/scripts/normalize-latex.py --target <target> --snapshot <run-dir>/before.md --report <run-dir>/latex-refinement-report.json [--only ...]`.
5. Return the report path, `valid`, `pages_changed`, `transform_counts`, `review_items`, and `refined_sha256`. Confirm the target's on-disk hash equals `refined_sha256`.

If the report is not valid, the note has already been restored from `before.md`; do not retry by hand and do not edit math manually. Do not create a second Markdown file, backup, report, or dot-prefixed path inside the vault.
