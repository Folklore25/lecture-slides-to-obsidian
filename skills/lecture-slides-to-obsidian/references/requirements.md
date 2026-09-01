# Prerequisite skills

This skill orchestrates note/CLI skills, the independent Canvas designer subskill, the official `mineru-open-api` CLI, and OpenSSL + macOS Keychain credential storage. The machine-readable sources of truth are [../requirements/skills.yaml](../requirements/skills.yaml), [../requirements/services.yaml](../requirements/services.yaml), and [../requirements/tools.yaml](../requirements/tools.yaml).

## Required skills

### `obsidian-markdown`

Use it after official CLI extraction to normalize and verify Obsidian Flavored Markdown: properties, wikilinks, embeds, callouts, comments, math delimiters, and vault-relative references. It does not parse PDFs, call MinerU, or decide course destinations.

### `obsidian-cli`

Use it for vault-native note operations and final artifact verification. The delegated Canvas designer also loads it for real DOM measurement.

### `obsidian-canvas-designer`

Delegate all Canvas layout, styling, static aesthetic scoring, local DOM measurement, and reflow to this sibling skill. The main Agent owns the semantic recall model and final package validation; it must not redraw the Canvas after the subagent returns PASS.

## Optional skill

### `slide-layout-refiner`

Load only when the user enables multimodal slide-layout refinement. It reads the original PDF visually and produces a staging candidate; it may modify syntax and same-page asset placement only. Preferred model is `MiniMax-M3`. If multimodal access or validation is unavailable, keep the base MinerU Markdown rather than guessing.

## Required service

Use only authenticated precision extraction through the official `mineru-open-api` CLI. Do not use the unauthenticated flash mode, direct HTTP, a local MinerU runtime, or a third-party wrapper.

## Required local tool

Obsidian CLI, `mineru-open-api`, OpenSSL with `aes-256-cbc`, and macOS Keychain's `security` CLI are required. Verify all four. Do not substitute screenshots, plaintext files, or same-directory encryption keys.

## Preflight

Before uploading course content:

1. Inspect the available skill list for exact names `obsidian-markdown`, `obsidian-cli`, and `obsidian-canvas-designer`, then explicitly invoke all three. The Canvas subagent separately loads `json-canvas` and `obsidian-cli` as required by its own contract.
2. Verify `obsidian version`, the workstation render profile, `mineru-open-api version`, OpenSSL, macOS Keychain, and `state/mineru-api-token.enc.json`.
3. If encrypted state is absent, send the chat-provided token through stdin to `scripts/token-store.py set --token-stdin`. The script creates the Keychain wrapping key automatically; never place the token in command arguments.
4. Validate the local file type and size against `requirements/services.yaml` without parsing its content locally.
5. Load the encrypted token automatically. Do not ask for repeated consent or another secret.
6. If any required skill, the local renderer profile, OpenSSL, Keychain, network access, or encrypted token state is unavailable, stop and report the exact requirement. Do not inline Canvas drawing into the main workflow, use screenshot QA, store plaintext secrets, or fall back to local parsing.

Run `scripts/preflight.py` and pass `--loaded-skill obsidian-markdown --loaded-skill obsidian-cli --loaded-skill obsidian-canvas-designer`; its JSON output is the machine-readable record that helper skills were loaded.

The manifests are declarative. Enforcement belongs to this preflight and future contract tests.

## Invocation boundary

`mineru-cli-adapter.py` imports `load_token_auto()`, injects plaintext only into the CLI child environment, and never prints it. The official CLI creates raw Markdown/assets/JSON in staging. Use `obsidian-markdown` for final note shaping, `obsidian-cli` for vault operations, and `obsidian-canvas-designer` for the delegated Canvas artifact. Preserve CLI warnings and provenance instead of hiding uncertainty.
