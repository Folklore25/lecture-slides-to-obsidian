# Prerequisite skills

This skill orchestrates three Obsidian skills, the official `mineru-open-api` CLI, the local Obsidian renderer, and OpenSSL + macOS Keychain credential storage. The machine-readable sources of truth are [../requirements/skills.yaml](../requirements/skills.yaml), [../requirements/services.yaml](../requirements/services.yaml), and [../requirements/tools.yaml](../requirements/tools.yaml).

## Required skills

### `obsidian-markdown`

Use it after official CLI extraction to normalize and verify Obsidian Flavored Markdown: properties, wikilinks, embeds, callouts, comments, math delimiters, and vault-relative references. It does not parse PDFs, call MinerU, or decide course destinations.

### `json-canvas`

Use it to create and validate the per-document knowledge-recall Canvas. It owns JSON Canvas syntax, IDs, nodes, edges, layout, file-node paths, and reference integrity. This composition skill owns the semantic recall model; neither skill may infer unsupported relationships or link the source original.

### `obsidian-cli`

Use it after Canvas generation to open the real file in the running local Obsidian app, mount every text card, inspect rendered DOM dimensions, and enforce the workstation render profile. Do not replace this with screenshots or source-text estimation.

## Required service

Use only authenticated precision extraction through the official `mineru-open-api` CLI. Do not use the unauthenticated flash mode, direct HTTP, a local MinerU runtime, or a third-party wrapper.

## Required local tool

Obsidian CLI, `mineru-open-api`, OpenSSL with `aes-256-cbc`, and macOS Keychain's `security` CLI are required. Verify all four. Do not substitute screenshots, plaintext files, or same-directory encryption keys.

## Preflight

Before uploading course content:

1. Inspect the harness's available skill list for exact names `obsidian-markdown`, `json-canvas`, and `obsidian-cli`, then explicitly invoke the Skill tool for all three and read each `SKILL.md` completely. Merely seeing them in the available list is not sufficient.
2. Verify `obsidian version`, the workstation render profile, `mineru-open-api version`, OpenSSL, macOS Keychain, and `state/mineru-api-token.enc.json`.
3. If encrypted state is absent, send the chat-provided token through stdin to `scripts/token-store.py set --token-stdin`. The script creates the Keychain wrapping key automatically; never place the token in command arguments.
4. Validate the local file type and size against `requirements/services.yaml` without parsing its content locally.
5. Load the encrypted token automatically. Do not ask for repeated consent or another secret.
6. If any Obsidian skill, the local renderer profile, OpenSSL, Keychain, network access, or encrypted token state is unavailable, stop and report the exact requirement. Do not use screenshot QA, plaintext storage, or local parsing.

Run `scripts/preflight.py` and pass `--loaded-skill obsidian-markdown --loaded-skill json-canvas --loaded-skill obsidian-cli`; its JSON output is the machine-readable record that helper skills were loaded.

The manifests are declarative. Enforcement belongs to this preflight and future contract tests.

## Invocation boundary

`mineru-cli-adapter.py` imports `load_token_auto()`, injects plaintext only into the CLI child environment, and never prints it. The official CLI creates raw Markdown/assets/JSON in staging. Use `obsidian-markdown` for final note shaping, `json-canvas` for relationship mapping, and `obsidian-cli` for real-renderer QA. Preserve CLI warnings and provenance instead of hiding uncertainty.
