# Tests

Phase one tests validate the repository and skill contracts. They do not test PDF extraction because no backend is implemented.

Future test layers should be separated:

1. **Structure tests** — skill metadata, required references, and portable paths.
2. **Prerequisite tests** — Obsidian skill availability, upload disclosure, plaintext token collection, and no local fallback.
3. **MinerU API contract tests** — signed upload, header isolation, bounded polling, secret handling, errors, and safe ZIP extraction.
4. **Course-routing tests** — first binding, aliases, active semesters, ambiguity, stale roots, containment, and collisions.
5. **API normalization tests** — MinerU ZIP artifacts to the shared intermediate representation.
6. **Golden tests** — deterministic Markdown/assets from redistributable fixtures.
7. **Visual review cases** — diagrams, tables, equations, OCR, and mixed-language pages.
8. **End-to-end tests** — source PDF to official API to validated Obsidian artifact set.

Run the current checks from the repository root:

```bash
./scripts/validate.sh
```
