# Bundled scripts

This directory contains deterministic Agent-facing orchestration helpers. MinerU extraction remains remote; no script parses the source document locally.

- `purge-state.sh --confirm` removes the registry, encrypted token, and their in-skill backups before uninstall. It does not touch course files or any path outside `state/`.
- `token-store.py set|verify|status|delete` manages ciphertext in skill state and its wrapping key in macOS Keychain without printing the token. API clients import `load_token_auto()`.
- `preflight.py` checks source/vault containment, file limits, loaded helper skills, encrypted token state, and staged confirmation fields; it returns JSON questions/errors.
- `fill-report.py --context <ctx.json> --output <staging>/conversion-report.md` renders deterministic temporary QA Markdown and rejects secret/path fields.
- `reconstruct-note.py` converts page-grouped MinerU V2 blocks into complete profile-aware Markdown plus normalization context.
- `build-canvas.py` turns the complete note headings/assets into a deterministic vault-relative JSON Canvas.
- `validate-output.py <document-folder> --vault-root <vault-root> --report <staging-report>` validates final artifacts; `--delete-report-on-success` removes temporary QA.

Future scripts belong here only when they provide deterministic, reusable behavior such as:

- calling the official MinerU Precision API without exposing the plaintext token;
- requesting signed upload URLs and uploading without forwarding Authorization;
- bounded polling and secret-safe result download;
- safe ZIP extraction;
- downloading and safely extracting MinerU result archives.

Each executable must document inputs, outputs, exit codes, token transport, network behavior, secret redaction, and overwrite rules. It must have tests before `SKILL.md` instructs an agent to run it. No script may implement local PDF parsing.
