# Official MinerU CLI composition (optional aid)

**Use this path only with `--extraction mineru`.** Native multimodal reading is the default and needs no CLI, no upload, and no credential.

Canonical client: <https://github.com/opendatalab/MinerU-Ecosystem/tree/main/cli/mineru-open-api>

The official `mineru-open-api` CLI owns authenticated submission, signed upload, polling, backoff, result download, and Markdown/assets extraction. This skill must not reimplement or directly call MinerU HTTP endpoints.

## When to choose it

- You want machine-readable page groups instead of reading every page yourself.
- The document is long, or its text layer is the only reliable source.
- The user explicitly asks for MinerU.
- The current model cannot view the source pages. Use `--extraction mineru` rather than guessing from a thumbnail-free reading.

## Installation and verification

```text
npm install -g mineru-open-api
uv tool install mineru-open-api
```

Verify with `mineru-open-api version`. `scripts/preflight.py` fails closed when the executable is missing **and** `--extraction mineru` was selected.

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

The official CLI saves `<source-stem>.md` plus downloaded assets, and `<source-stem>.json`, the content-list representation.

The adapter groups the CLI JSON by `page_idx` and writes `<source-stem>.content-list-v2.compat.json`. It also renames referenced visuals, copies them into `normalized-assets/`, and writes staging-only `<source-stem>.asset-map.json`. These transformations are deterministic and do not infer new content.

That page-group file feeds two consumers:

- `scripts/plan-note-structure.py --page-groups ...`, which proposes a section skeleton and enables per-page text recall during validation.
- `scripts/reconstruct-note.py`, which produces the marker-based transcription used by `policy-document` and `paper` in MinerU mode.

Preserve the original CLI Markdown and JSON in staging for QA; only the delivered notes, Canvas files, and chosen assets enter the vault.

## Failure and logging

- Keep CLI stdout/stderr separate and redact the token defensively.
- Do not enable `--verbose`; HTTP debugging may expose sensitive request details.
- A non-zero CLI exit is an extraction failure; do not fall back to direct HTTP or local parsing.
- Timeout, authentication, size/page-limit, and unsupported-format handling belong to the official CLI. Report its redacted error and stop.
- Staging artifacts are recoverable QA state and are removed when the task completes or is abandoned.
