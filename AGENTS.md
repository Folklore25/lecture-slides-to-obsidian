# Repository maintenance instructions

- Treat `skills/lecture-slides-to-obsidian/` as the distributable skill payload.
- Keep `SKILL.md` concise; route conditional detail to `references/`.
- The official `mineru-open-api` precision CLI is the only extraction client. Never add direct MinerU HTTP code, a local parser/runtime, or lightweight fallback.
- Keep source originals outside the Obsidian vault; only complete Markdown, derived assets, and knowledge-recall Canvas belong in document folders.
- Conversion reports and recall models are temporary Agent QA state outside the vault. Extract final-response facts, then delete both after successful validation.
- Use the official CLI JSON output grouped by `page_idx`; never derive page boundaries with global Markdown anchors.
- Enforce `page-PPP-kind-NN.ext` final asset names and keep `asset-map.json` in staging only.
- Never build a Canvas from heading order. Require a coverage-complete semantic recall model, meaningful relation labels, a connected selective graph, and memory-critical assets only.
- Canvas readability is not complete until local Obsidian DOM measurement drives a second layout pass and the final check confirms measured height margin plus 16px effective reading font. Do not use screenshots by default.
- Keep structural alignment separate from pixel-level visual comparison; mark unperformed rendering `NOT-CHECKED`.
- Keep course routing behavior aligned across `course-routing.md`, the registry example, output contract, examples, and routing test cases.
- Never store a user's real semester root or course paths in the repository.
- Keep prerequisite declarations aligned across `SKILL.md` metadata, requirements manifests, `requirements.md`, `mineru-cli.md`, and contract tests.
- Persist the MinerU token only through `scripts/token-store.py`: ciphertext in ignored skill state, wrapping key in macOS Keychain. Never persist plaintext or log signed URLs.
- Keep runtime state inside the distributable skill's `state/` directory and never reintroduce a user-level registry path.
- Never commit private or copyrighted lecture PDFs without explicit redistribution rights.
- Update the output contract, examples, tests, and README together when a public behavior changes.
- Run `./scripts/validate.sh` before reporting repository work complete.
