# Prerequisite skills

This skill orchestrates note/CLI skills, the independent Canvas designer subskill, and either native multimodal reading (default) or the official `mineru-open-api` CLI. Machine-readable sources of truth: [../requirements/skills.yaml](../requirements/skills.yaml), [../requirements/services.yaml](../requirements/services.yaml), [../requirements/tools.yaml](../requirements/tools.yaml).

## Capability split

| Capability | `--extraction native` (default) | `--extraction mineru` |
| --- | --- | --- |
| Natively multimodal model that can read the source pages | **required** | not required |
| `mineru-open-api` CLI | not required | **required** |
| OpenSSL, macOS Keychain, encrypted token state | not required | **required** |
| MinerU language and OCR confirmation | not applicable | **required** |
| Obsidian CLI + skills, Canvas designer | **required** | **required** |

Native mode removes the upload, the credential, and the text-layer dependency. It does not remove the Obsidian CLI, the Canvas designer, or the renderer QA.

## Required skills

### `obsidian-markdown`

Normalize and verify Obsidian Flavored Markdown: properties, wikilinks, embeds, callouts, comments, math delimiters, and vault-relative references. It does not read PDFs, call MinerU, or decide course destinations.

### `obsidian-cli`

Vault-native note operations and final artifact verification. The delegated Canvas designer also loads it for real DOM measurement.

### `obsidian-canvas-designer`

Delegate all Canvas layout, styling, static aesthetic scoring, local DOM measurement, and reflow to this sibling skill. The main Agent owns the semantic recall model and final package validation; it must not redraw the Canvas after the subagent returns PASS.

## Optional skills

### `obsidian-latex-refiner`

Load only when the user enables LaTeX normalization. Run the read-only `--analyze` scan first, decide which transform groups are safe, then apply them in place. An independent validator enforces conservation of visible non-math text, links, and assets and restores the byte-exact outside-vault snapshot on any failure. It needs no vision model and treats a marker-free note as a single segment.

## Required service (MinerU mode only)

Use only authenticated precision extraction through the official `mineru-open-api` CLI. Do not use unauthenticated flash mode, direct HTTP, a local MinerU runtime, or a third-party wrapper.

## Required local tools

- Always: Obsidian CLI for renderer QA.
- MinerU mode only: `mineru-open-api`, OpenSSL with `aes-256-cbc`, and macOS Keychain's `security` CLI.

## Preflight

1. Inspect the available skill list for exact names `obsidian-markdown`, `obsidian-cli`, and `obsidian-canvas-designer`, then explicitly invoke all three. Invoke `obsidian-latex-refiner` only when LaTeX normalization is enabled.
2. Confirm the extraction mode and, when native, that the current model can view the source pages.
3. Resolve every path against the installed skill directory (the directory containing the loaded SKILL.md).
4. In MinerU mode, run `scripts/token-store.py status` before asking for a token: `configured` means proceed silently. Only when status reports `not configured`, send the chat-provided token through stdin to `scripts/token-store.py set --token-stdin`. Never place the token in command arguments or environment profiles.
5. Validate the local file type and size without parsing its content locally.
6. If any requirement for the selected mode is unavailable, stop and report the exact requirement. Do not inline Canvas drawing, use screenshot QA, store plaintext secrets, or fall back to local parsing.

Run `scripts/preflight.py` and pass `--loaded-skill obsidian-markdown --loaded-skill obsidian-cli --loaded-skill obsidian-canvas-designer`; its JSON output is the machine-readable record of the decisions and helper skills.

## Invocation boundary

`mineru-cli-adapter.py` imports `load_token_auto()`, injects plaintext only into the CLI child environment, and never prints it. Use `obsidian-markdown` for note shaping, `obsidian-cli` for vault operations, and `obsidian-canvas-designer` for the delegated Canvas artifact. Preserve CLI warnings and provenance instead of hiding uncertainty.
