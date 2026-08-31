# Bundled scripts

This directory contains only state cleanup in phase one; it remains empty of conversion code.

- `purge-state.sh --confirm` removes the registry, encrypted token, and their in-skill backups before uninstall. It does not touch course files or any path outside `state/`.
- `token-store.py set|verify|status|delete` manages the encrypted MinerU token without printing it. API clients import `load_token()` and keep plaintext in memory only.
- `validate-output.py <document-folder> [--vault-root <vault-root>]` validates a completed derived folder without modifying it.

Future scripts belong here only when they provide deterministic, reusable behavior such as:

- calling the official MinerU Precision API without exposing the plaintext token;
- requesting signed upload URLs and uploading without forwarding Authorization;
- bounded polling and secret-safe result download;
- safe ZIP extraction;
- normalizing extracted assets and links;
- validating the output contract;
- producing a machine-readable conversion report.

Each executable must document inputs, outputs, exit codes, token transport, network behavior, secret redaction, and overwrite rules. It must have tests before `SKILL.md` instructs an agent to run it. No script may implement local PDF parsing.
