# Prerequisite skills

This skill orchestrates two Obsidian skills, OpenSSL + macOS Keychain credential storage, and the official MinerU Precision API. The machine-readable sources of truth are [../requirements/skills.yaml](../requirements/skills.yaml), [../requirements/services.yaml](../requirements/services.yaml), and [../requirements/tools.yaml](../requirements/tools.yaml).

## Required skills

### `obsidian-markdown`

Use it after API extraction to normalize and verify Obsidian Flavored Markdown: properties, wikilinks, embeds, callouts, comments, math delimiters, and vault-relative references. It does not parse PDFs, call MinerU, or decide course destinations.

### `json-canvas`

Use it to create and validate the per-document relationship canvas. It owns JSON Canvas syntax, IDs, nodes, edges, layout, file-node paths, and reference integrity. It does not infer unsupported relationships or link the source original.

## Required service

Use only the authenticated MinerU Precision API v4 documented at `https://mineru.net/apiManage/docs`. Do not use the unauthenticated Agent lightweight API, a local MinerU runtime, or a third-party wrapper.

## Required local tool

OpenSSL with `aes-256-cbc` support and macOS Keychain's `security` CLI are required for automatic credential storage. Verify both tools. Do not substitute plaintext files or same-directory encryption keys.

## Preflight

Before uploading course content:

1. Inspect the harness's available skill list for exact names `obsidian-markdown` and `json-canvas`, then explicitly invoke the Skill tool for both and read each `SKILL.md` completely. Merely seeing them in the available list is not sufficient.
2. Verify OpenSSL, macOS Keychain, and `state/mineru-api-token.enc.json`.
3. If encrypted state is absent, send the chat-provided token through stdin to `scripts/token-store.py set --token-stdin`. The script creates the Keychain wrapping key automatically; never place the token in command arguments.
4. Validate the local file type and size against `requirements/services.yaml` without parsing its content locally.
5. Load the encrypted token automatically. Do not ask for repeated consent or another secret.
6. If either Obsidian skill, OpenSSL, Keychain, network access, or encrypted token state is unavailable, stop and report the exact requirement. Do not use plaintext storage or fall back to local parsing.

Run `scripts/preflight.py` and pass `--loaded-skill obsidian-markdown --loaded-skill json-canvas`; its JSON output is the machine-readable record that helper skills were loaded.

The manifests are declarative. Enforcement belongs to this preflight and future contract tests.

## Invocation boundary

The API client imports `load_token_auto()` from `scripts/token-store.py`, uses plaintext only in process memory, and never prints it. It then creates raw extraction artifacts in staging. Use `obsidian-markdown` for final note shaping and `json-canvas` for relationship mapping. Preserve API warnings and provenance instead of allowing normalization to hide uncertainty.
