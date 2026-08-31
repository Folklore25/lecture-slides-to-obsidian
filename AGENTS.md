# Repository maintenance instructions

- Treat `skills/lecture-slides-to-obsidian/` as the distributable skill payload.
- Keep `SKILL.md` concise; route conditional detail to `references/`.
- Do not claim a conversion backend exists until its script, dependency contract, and tests are present.
- Keep course routing behavior aligned across `course-routing.md`, the registry example, output contract, examples, and routing test cases.
- Never store a user's real semester root or course paths in the repository.
- Keep prerequisite declarations aligned across `SKILL.md` metadata, `requirements/skills.yaml`, `requirements.md`, and prerequisite test cases.
- Keep runtime state inside the distributable skill's `state/` directory and never reintroduce a user-level registry path.
- Never commit private or copyrighted lecture PDFs without explicit redistribution rights.
- Update the output contract, examples, tests, and README together when a public behavior changes.
- Run `./scripts/validate.sh` before reporting repository work complete.
