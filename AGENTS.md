# Repository maintenance instructions

- Treat `skills/lecture-slides-to-obsidian/` as the distributable skill payload.
- Keep `SKILL.md` concise; route conditional detail to `references/`.
- The official MinerU Precision API v4 is the only extraction backend. Never add a local parser, local MinerU runtime, or lightweight API fallback.
- Keep course routing behavior aligned across `course-routing.md`, the registry example, output contract, examples, and routing test cases.
- Never store a user's real semester root or course paths in the repository.
- Keep prerequisite declarations aligned across `SKILL.md` metadata, both requirements manifests, `requirements.md`, `mineru-api.md`, and contract test cases.
- Treat plaintext API tokens and signed upload/result URLs as secrets: never commit, persist, echo, or log them.
- Keep runtime state inside the distributable skill's `state/` directory and never reintroduce a user-level registry path.
- Never commit private or copyrighted lecture PDFs without explicit redistribution rights.
- Update the output contract, examples, tests, and README together when a public behavior changes.
- Run `./scripts/validate.sh` before reporting repository work complete.
