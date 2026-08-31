# Official MinerU CLI composition

Canonical client: <https://github.com/opendatalab/MinerU-Ecosystem/tree/main/cli/mineru-open-api>

The official `mineru-open-api` CLI owns authenticated submission, signed upload, polling, backoff, result download, and Markdown/assets extraction. This skill must not reimplement or directly call MinerU HTTP endpoints.

## Installation and verification

Install using one supported channel:

```text
npm install -g mineru-open-api
uv tool install mineru-open-api
```

Verify with `mineru-open-api version`. `scripts/preflight.py` fails closed when the executable is missing.

## Credential composition

Do not run `mineru-open-api auth`; that writes a token to `~/.mineru/config.yaml`, outside the skill-owned state boundary.

`scripts/mineru-cli-adapter.py` calls `load_token_auto()` and injects the plaintext only into the child process environment as `MINERU_TOKEN`. It also sets `MINERU_SOURCE=lecture-slides-to-obsidian`. Never use the CLI `--token` flag, verbose mode, shell history, or a plaintext config file.

## Adapter invocation

After preflight confirms language and OCR:

```text
scripts/mineru-cli-adapter.py <source-file> \
  --output-dir <staging>/mineru \
  --language <confirmed-language> \
  --is-ocr <true-or-false> \
  --model vlm \
  --timeout 300
```

The adapter runs the equivalent official command:

```text
mineru-open-api extract <source-file> -o <staging-dir>/ \
  -f md,json --model vlm --language <value> \
  --formula=true --table=true --timeout 300 [--ocr]
```

The trailing separator on `-o` forces directory output. Do not use `flash-extract`: course materials require precision Markdown, images, tables, formulas, and JSON.

## Output boundary

The official CLI saves:

- `<source-stem>.md` plus downloaded assets;
- `<source-stem>.json`, the CLI/SDK content-list representation.

The adapter groups the CLI JSON by `page_idx` and writes `<source-stem>.content-list-v2.compat.json`, a page-grouped compatibility artifact consumed by `reconstruct-note.py`. It also collects downloaded images into `normalized-assets/` for the final document `assets/` directory. These transformations are deterministic and do not infer new content.

`source_pages` is the normalized page-group count. Preserve the original CLI Markdown and JSON in staging for QA; only normalized Markdown/assets/Canvas enter the vault.

## Failure and logging

- Keep CLI stdout/stderr separate and redact the token defensively.
- Do not enable `--verbose`; HTTP debugging may expose sensitive request details.
- A non-zero CLI exit is an extraction failure; do not fall back to direct HTTP or local parsing.
- Timeout, authentication, size/page-limit, and unsupported-format handling belong to the official CLI. Report its redacted error and stop.
- Staging artifacts are recoverable QA state and are removed when the task completes or is abandoned.
