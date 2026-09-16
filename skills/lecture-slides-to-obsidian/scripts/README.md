# Bundled scripts

Deterministic Agent-facing orchestration helpers. No script parses the source document locally: native reading is the model's job, and MinerU extraction is remote.

- `preflight.py` — checks source/vault containment, loaded helper skills, extraction mode, note granularity, native visual capability, and (MinerU mode only) token state and CLI presence. Returns JSON `questions[]`, `errors[]`, and `checks{}`.
- `plan-note-structure.py` — the skeleton planner and the single source of truth for the note structure. Drafts `note-plan.json` and `page-ledger.json` from `--page-count` (native) or `--page-groups` (MinerU), validates finalized versions with `--check-plan`/`--check-ledger`, and owns the ledger schema, drop-reason vocabulary, and evidence requirement.
- `validate-output.py` — validates the delivered folder. It loads the planner module so plan and ledger rules stay in one place. `--plan`/`--ledger` select the content-driven contract; without them the MinerU page-marker contract applies. `--delete-qa-on-success` removes every temporary QA file.
- `fill-report.py --context <ctx.json> --output <staging>/conversion-report.md` — renders deterministic temporary QA Markdown and rejects secret or absolute-path fields.
- `plan-canvas-batch.py` — validates isolated one-note Canvas tasks, requires subagent delegation for two or more notes, and reserves a single renderer lane.
- `mineru-cli-adapter.py` — MinerU mode only. Injects the Keychain token into the official CLI, requests `md,json`, and converts legacy `page_idx` output into page groups plus an asset map.
- `reconstruct-note.py` — MinerU mode only. Converts page-grouped MinerU blocks into profile-aware Markdown with page markers for `policy-document` and `paper`.
- `token-store.py set|verify|status|delete` — manages ciphertext in skill state and its wrapping key in macOS Keychain without printing the token. The CLI adapter imports `load_token_auto()`.
- `purge-state.sh --confirm` — removes the registry, encrypted token, and their in-skill backups before uninstall. It does not touch course files or any path outside `state/`.
- Canvas build, aesthetics, and renderer scripts live in the sibling `obsidian-canvas-designer` skill.
- Deterministic LaTeX normalization and its conservation validator live in the sibling `obsidian-latex-refiner` skill.

Do not add custom MinerU HTTP/upload/polling scripts. Improve the thin CLI adapter or the upstream official CLI instead.

Each executable must document inputs, outputs, exit codes, token transport, network behavior, secret redaction, and overwrite rules. It must have tests before `SKILL.md` instructs an agent to run it. No script may implement local PDF parsing.
