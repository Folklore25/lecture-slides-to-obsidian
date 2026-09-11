Run `$obsidian-latex-refiner` deterministically; no vision model is required.

Inputs:

- target Markdown: <absolute-final-markdown-path-in-vault>
- vault root: <absolute-vault-root>
- run directory: <absolute-run-directory-outside-vault>

Steps:

1. Prove the run directory resolves outside the vault.
2. Run `python3 <skill-dir>/scripts/normalize-latex.py --target <target> --vault-root <vault-root> --snapshot <run-dir>/before.md --report <run-dir>/latex-refinement-report.json`.
3. If the report `valid` is false, the target has already been restored from `<run-dir>/before.md`; do not retry by hand and do not edit math manually.
4. If `valid` is true, return the target path, the report path, `valid`, `pages_changed`, `transform_counts`, and `review_items`.

Do not create a second Markdown file, backup, report, or dot-prefixed path inside the vault. Do not change visible text, math payloads, page markers, links, assets, or Callouts.
