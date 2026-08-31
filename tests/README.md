# Tests

Phase one tests validate repository contracts plus one synthetic derived document folder. They do not call the live MinerU API.

Future test layers should be separated:

1. **Structure tests** — skill metadata, required references, and portable paths.
2. **Prerequisite tests** — Obsidian skills, OpenSSL/Keychain capability, encrypted token setup/automatic unlock, and no plaintext/local fallback.
3. **Token-store tests** — encryption round-trip, mode 0600, Keychain wrapping key, tamper detection, and scoped deletion.
4. **MinerU API contract tests** — encrypted credentials, signed upload, header isolation, bounded polling, errors, and safe ZIP extraction.
5. **Course-routing tests** — first binding, aliases, active semesters, ambiguity, stale roots, containment, and collisions.
6. **API normalization tests** — page-grouped content lists, legacy `page_idx`, duplicate anchors, heading levels, and auxiliary blocks.
7. **Canvas tests** — profile-specific relationship nodes/edges and source-original exclusion.
8. **Output-validator tests** — folder, Markdown, Canvas, assets, report, and NOT-CHECKED semantics.
9. **Golden tests** — deterministic Markdown/assets from redistributable fixtures.
10. **Visual review cases** — diagrams, tables, equations, OCR, and mixed-language pages.
11. **End-to-end tests** — source file outside vault to official API to validated Obsidian folder.

The current offline integration test covers V2 reconstruction → Canvas build → temporary report render → validation → report deletion. Live MinerU network calls remain out of test scope.

Run the current checks from the repository root:

```bash
./scripts/validate.sh
```
