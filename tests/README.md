# Tests

Phase one tests validate repository contracts plus one synthetic derived document folder. They do not call the live MinerU API.

Future test layers should be separated:

1. **Structure tests** — skill metadata, required references, and portable paths.
2. **Prerequisite tests** — Obsidian skills/CLI, workstation render profile, OpenSSL/Keychain capability, encrypted token setup/automatic unlock, and no plaintext/local fallback.
3. **Token-store tests** — encryption round-trip, mode 0600, Keychain wrapping key, tamper detection, and scoped deletion.
4. **MinerU CLI adapter tests** — child-env credentials, official command flags, output discovery, legacy page grouping, redaction, and fail-closed behavior.
5. **Course-routing tests** — first binding, aliases, active semesters, ambiguity, stale roots, containment, and collisions.
6. **API normalization tests** — page-grouped content lists, legacy `page_idx`, duplicate anchors, heading levels, and auxiliary blocks.
7. **Canvas subskill tests** — semantic model validation, Axton-informed density/color/edge gates, deterministic layout, delegation boundaries, and source-original exclusion.
8. **Canvas renderer tests** — foreground DOM enforcement, measured height formula, safety rounding, local profile mismatch, effective font size, and stale-check rejection.
9. **Output-validator tests** — folder, Markdown, Canvas, assets, all temporary QA files, and NOT-CHECKED semantics.
10. **Golden tests** — deterministic Markdown/assets from redistributable fixtures.
11. **Visual review cases** — diagrams, tables, equations, OCR, and mixed-language pages.
12. **End-to-end tests** — source file outside vault to official API to validated Obsidian folder.

The automated integration test covers V2 reconstruction → Canvas subskill build/aesthetic check → temporary report render → validation → QA-state deletion. Local workstation experiments additionally verify foreground Obsidian DOM measure → rebuild/reflow → aesthetic recheck → DOM check without screenshots. Live MinerU network calls remain out of test scope.

Run the current checks from the repository root:

```bash
./scripts/validate.sh
```
