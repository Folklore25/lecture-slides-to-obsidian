# Tests

Phase one tests validate repository contracts plus one synthetic derived document folder. They do not call the live MinerU API.

Future test layers should be separated:

1. **Structure tests** — skill metadata, required references, and portable paths.
2. **Prerequisite tests** — Obsidian skill availability, upload disclosure, plaintext token collection, and no local fallback.
3. **MinerU API contract tests** — signed upload, header isolation, bounded polling, secret handling, errors, and safe ZIP extraction.
4. **Course-routing tests** — first binding, aliases, active semesters, ambiguity, stale roots, containment, and collisions.
5. **API normalization tests** — page-grouped content lists, legacy `page_idx`, duplicate anchors, heading levels, and auxiliary blocks.
6. **Canvas tests** — profile-specific relationship nodes/edges and source-original exclusion.
7. **Output-validator tests** — folder, Markdown, Canvas, assets, report, and NOT-CHECKED semantics.
8. **Golden tests** — deterministic Markdown/assets from redistributable fixtures.
9. **Visual review cases** — diagrams, tables, equations, OCR, and mixed-language pages.
10. **End-to-end tests** — source file outside vault to official API to validated Obsidian folder.

Run the current checks from the repository root:

```bash
./scripts/validate.sh
```
