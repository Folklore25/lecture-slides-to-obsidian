# Prerequisite skills

This skill orchestrates two Obsidian skills, OpenSSL-backed encrypted credential storage, and the official MinerU Precision API. The machine-readable sources of truth are [../requirements/skills.yaml](../requirements/skills.yaml), [../requirements/services.yaml](../requirements/services.yaml), and [../requirements/tools.yaml](../requirements/tools.yaml).

## Required skills

### `obsidian-markdown`

Use it after API extraction to normalize and verify Obsidian Flavored Markdown: properties, wikilinks, embeds, callouts, comments, math delimiters, and vault-relative references. It does not parse PDFs, call MinerU, or decide course destinations.

### `json-canvas`

Use it to create and validate the per-document relationship canvas. It owns JSON Canvas syntax, IDs, nodes, edges, layout, file-node paths, and reference integrity. It does not infer unsupported relationships or link the source original.

## Required service

Use only the authenticated MinerU Precision API v4 documented at `https://mineru.net/apiManage/docs`. Do not use the unauthenticated Agent lightweight API, a local MinerU runtime, or a third-party wrapper.

## Required local tool

OpenSSL with `aes-256-cbc` support is required only for the encrypted token store. Verify it with `openssl version` and `openssl enc -list`. Do not substitute plaintext files or reversible encoding when it is unavailable.

## Preflight

Before uploading course content:

1. Inspect the harness's available skill list for exact names `obsidian-markdown` and `json-canvas`, then load both completely.
2. Verify OpenSSL and `state/mineru-api-token.enc.json`.
3. If encrypted state is absent, run `scripts/token-store.py set`. The script must collect the token and a 12+ character encryption passphrase through hidden prompts; do not place either in command arguments.
4. Validate the local file type and size against `requirements/services.yaml` without parsing its content locally.
5. Tell the user that the file will be uploaded to MinerU, then unlock the encrypted token through a hidden passphrase prompt.
6. If either Obsidian skill, OpenSSL, network access, encrypted token, or passphrase is unavailable, stop and report the exact requirement. Do not use plaintext storage or fall back to local parsing.

The manifests are declarative. Enforcement belongs to this preflight and future contract tests.

## Invocation boundary

The API client imports `load_token()` from `scripts/token-store.py`, uses the plaintext only in process memory, and never prints it. It then creates raw extraction artifacts in staging. Use `obsidian-markdown` for final note shaping and `json-canvas` for relationship mapping. Preserve API warnings and provenance instead of allowing normalization to hide uncertainty.
