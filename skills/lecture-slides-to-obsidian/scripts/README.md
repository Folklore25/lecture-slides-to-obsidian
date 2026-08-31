# Bundled scripts

This directory contains deterministic Agent-facing orchestration helpers. MinerU extraction remains remote; no script parses the source document locally.

- `purge-state.sh --confirm` removes the registry, encrypted token, and their in-skill backups before uninstall. It does not touch course files or any path outside `state/`.
- `token-store.py set|verify|status|delete` manages ciphertext in skill state and its wrapping key in macOS Keychain without printing the token. The CLI adapter imports `load_token_auto()`.
- `preflight.py` checks source/vault containment, file limits, loaded helper skills, encrypted token state, and staged confirmation fields; it returns JSON questions/errors.
- `mineru-cli-adapter.py` injects the Keychain token into the official CLI, requests `md,json`, and converts legacy `page_idx` output into page groups.
- `fill-report.py --context <ctx.json> --output <staging>/conversion-report.md` renders deterministic temporary QA Markdown and rejects secret/path fields.
- `reconstruct-note.py` converts page-grouped MinerU V2 blocks into complete profile-aware Markdown plus normalization context.
- `build-canvas.py` validates an Agent-authored staging recall model and renders a deterministic, vault-relative knowledge-recall Canvas. It does not infer meaning from heading order.
- `canvas-render-qa.py measure|check` uses the running local Obsidian DOM to measure card height and effective font size without screenshots.
- `validate-output.py <document-folder> --vault-root <vault-root> --report <staging-report> --recall-model <staging-model> --render-metrics <metrics> --render-check <check>` validates final artifacts; `--delete-qa-on-success` removes all temporary QA files.

Do not add custom MinerU HTTP/upload/polling scripts. Improve the thin CLI adapter or upstream official CLI instead.

Each executable must document inputs, outputs, exit codes, token transport, network behavior, secret redaction, and overwrite rules. It must have tests before `SKILL.md` instructs an agent to run it. No script may implement local PDF parsing.
