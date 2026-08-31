# Prerequisite skills

This skill orchestrates one separately installed skill and the official MinerU Precision API. The machine-readable sources of truth are [../requirements/skills.yaml](../requirements/skills.yaml) and [../requirements/services.yaml](../requirements/services.yaml).

## Required skills

### `obsidian-markdown`

Use it after API extraction to normalize and verify Obsidian Flavored Markdown: properties, wikilinks, embeds, callouts, comments, math delimiters, and vault-relative references. It does not parse PDFs, call MinerU, or decide course destinations.

## Required service

Use only the authenticated MinerU Precision API v4 documented at `https://mineru.net/apiManage/docs`. Do not use the unauthenticated Agent lightweight API, a local MinerU runtime, or a third-party wrapper.

## Preflight

Before uploading course content:

1. Inspect the harness's available skill list for the exact name `obsidian-markdown` and load it completely.
2. Validate the local file type and size against `requirements/services.yaml` without parsing its content locally.
3. Tell the user that the file will be uploaded to MinerU and that a plaintext token entered in the Agent input may remain in the host's conversation history.
4. Ask the user to paste the MinerU API token into the input box only after the task is ready to submit.
5. If the Obsidian skill, network access, or token is missing, stop and report the exact requirement. Do not install a substitute or fall back to local parsing.

The manifests are declarative. Enforcement belongs to this preflight and future contract tests.

## Invocation boundary

Use MinerU's official API to create raw extraction artifacts in staging. This skill then applies course routing and the shared output contract. Use `obsidian-markdown` for final note shaping and syntax verification. Preserve API warnings and provenance instead of allowing normalization to hide uncertainty.
