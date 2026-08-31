# Tests

Phase one tests validate the repository and skill contracts. They do not test PDF extraction because no backend is implemented.

Future test layers should be separated:

1. **Structure tests** — skill metadata, required references, and portable paths.
2. **Prerequisite tests** — required skill names, runtime availability, missing dependency behavior, and no implicit install.
3. **Course-routing tests** — first binding, aliases, active semesters, ambiguity, stale roots, containment, and collisions.
4. **Adapter unit tests** — backend raw output to shared intermediate representation.
5. **Golden tests** — deterministic Markdown/assets from redistributable fixtures.
6. **Visual review cases** — diagrams, tables, equations, OCR, and mixed-language pages.
7. **End-to-end tests** — source PDF to validated Obsidian artifact set.

Run the current checks from the repository root:

```bash
./scripts/validate.sh
```
