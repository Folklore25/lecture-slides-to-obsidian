# MinerU Precision API v4

Canonical documentation: <https://mineru.net/apiManage/docs>

This is the only PDF extraction backend for the skill. Local parsing, local MinerU models/CLI, third-party MinerU wrappers, and the unauthenticated lightweight Agent API are out of scope.

## Limits and defaults

- Maximum file size: 200 MB.
- Maximum document length: 200 pages.
- Maximum upload URLs requested at once: 50.
- Signed upload URLs are valid for 24 hours.
- Default `model_version`: `vlm`.
- Formula and table recognition are enabled.
- `language` has no API-request default in this skill. Infer from the user's description, filename/course context, or known document metadata, then confirm an actual MinerU language enum before submission. Never send the literal value `auto`.
- OCR has no hard-coded default. Confirm a boolean `is_ocr` for every document. Recommend true when the user identifies a scan, image-only document, or unreliable existing OCR; otherwise explain the tradeoff and ask.

## Encrypted token lifecycle

Persist the token only at:

```text
<skill-directory>/state/mineru-api-token.enc.json
```

`scripts/token-store.py` implements authenticated encryption using OpenSSL AES-256-CBC with PBKDF2-HMAC-SHA256 (600,000 iterations) and an independent Encrypt-then-HMAC-SHA256 integrity key. The passphrase is never stored. The encrypted file is mode `0600`; `state/` is mode `0700` when written.

First setup:

```text
scripts/token-store.py set
```

The script prompts for token and passphrase without echo. If the Agent already collected the token in its input box, pass it through stdin with `set --token-stdin`; never place it in command arguments. The conversation host may retain the original user message, which this skill cannot delete.

Later conversions ask only for the encryption passphrase through a hidden prompt. The API client imports `load_token()` and keeps plaintext in memory only. There is intentionally no CLI command that prints the token.

Rules:

- never repeat or quote any token/passphrase characters;
- never persist plaintext token/passphrase in registry, configuration, environment profiles, shell history, temporary files, reports, logs, or Git;
- do not create `/tmp/.mineru-token`, mode-0600 plaintext token files, `with-token.sh`, or `Bearer $(cat ...)` wrappers; encrypted state plus in-process `load_token()` supersedes them;
- never copy the encrypted file outside the installed skill state directory;
- send `Authorization: Bearer <token>` only to HTTPS requests whose origin is exactly `https://mineru.net`;
- on `A0202` or `A0211`, delete or replace the encrypted token through `token-store.py`; never show the rejected value;
- if the passphrase is lost, the token cannot be recovered locally—delete and recreate the encrypted file.

## Local-file submission

For one or more local PDFs:

1. `POST https://mineru.net/api/v4/file-urls/batch` with the Bearer token and JSON body.
2. Include one `files` entry per PDF, preserving the correct filename extension. Use a non-sensitive `data_id` if one is needed.
3. Capture `data.batch_id` and the ordered `data.file_urls` in memory only.
4. `PUT` each file's raw bytes to its matching signed URL. Do not set `Authorization` or `Content-Type` on the upload request.
5. Upload completion automatically submits extraction; do not call another submit endpoint.
6. Poll `GET https://mineru.net/api/v4/extract-results/batch/{batch_id}` with the Bearer token.

Example request shape with no secret values:

```json
{
  "files": [
    {
      "name": "lecture-03.pdf",
      "data_id": "is0000-lecture-03",
      "is_ocr": false
    }
  ],
  "model_version": "vlm",
  "enable_formula": true,
  "enable_table": true,
  "language": "ch"
}
```

This example assumes the user explicitly chose `language: ch` and `is_ocr: false`; neither is a default.

Do not use `POST /api/v4/extract/task` for a local file; that endpoint accepts a remotely accessible file URL and does not directly upload the file.

### Signed PUT header boundary

The signed OSS request expects the Content-Type component used by the signature to remain empty. Adding `Content-Type: application/pdf`, `multipart/form-data`, or another value can produce `403 SignatureDoesNotMatch`. Upload raw file bytes, not a multipart body. Never forward the MinerU Bearer token to the signed URL.

Equivalent diagnostic curl shape:

```bash
curl --fail-with-body --request PUT \
  --header 'Content-Type:' \
  --upload-file "$SOURCE_FILE" \
  "$SIGNED_UPLOAD_URL"
```

Keep both variables out of shell history and command transcripts; the future API client should perform this request in process rather than constructing a logged shell command.

## Poll response shape

The batch endpoint does not return a single `data.state`. Read:

```text
response.data.batch_id
response.data.extract_result[]
response.data.extract_result[i].state
response.data.extract_result[i].full_zip_url
response.data.extract_result[i].err_msg
```

Match each `extract_result` item to the submitted document using `data_id` when returned, otherwise the exact `file_name`. Never read `response.data.state` for a batch response.

Inspect the first poll response's keys and types in memory before entering the loop. If the expected list/state path is missing, stop immediately with a redacted schema diagnostic. If state remains unknown for 30 seconds, stop and show a redacted JSON structure or key/type tree. Do not dump raw responses containing result URLs.

## Backoff polling and result download

Use bounded backoff without printing every poll:

- elapsed 0–30 seconds: poll every 3 seconds;
- elapsed 31–120 seconds: poll every 10 seconds;
- elapsed above 120 seconds: poll every 30 seconds;
- default overall timeout: 300 seconds;
- default per-request network timeout: 30 seconds.

Report only state transitions, meaningful progress changes, terminal state, timeout, or schema failure. Handle `waiting-file`, `pending`, `running`, and `converting` as non-terminal; `done` and `failed` are terminal.

On `done`, read the matched item's `full_zip_url` and download it over HTTPS without the Bearer token. Never persist or print the full signed upload URL or result URL. A timeout is not a failed task: report the redacted `batch_id` and last known per-file state without continuing an unbounded polling loop.

On `failed`, report the documented error code/message after checking that no token or signed URL is present. Relevant failures include invalid/expired token (`A0202`, `A0211`), oversized file (`-60005`), too many pages (`-60006`), queue saturation (`-60009`), parsing failure (`-60010`), and daily task limit (`-60018`).

## Safe ZIP handling

Download the ZIP into staging. Before extraction, reject absolute member paths, `..` traversal, symlinks, device files, or any member resolving outside the staging directory. Enforce reasonable extracted-size and member-count limits.

Treat a nested ZIP/TAR/archive member as unexpected. Do not recursively extract it; reject the result or quarantine that member for explicit review. MinerU's expected outputs are Markdown, JSON, images, and related derived files, not another opaque archive layer.

Preserve the raw API artifacts, including `full.md`, images, `content_list.json`, and other JSON when present. Never treat a successful archive download as proof that every page was parsed correctly.

## Secret-safe reporting

The temporary staging report may contain the provider (`MinerU Precision API v4`), model, non-secret options, result state, and redacted task/batch reference. It must not contain the API token, Authorization header, signed upload URL, full result URL, or raw response headers, and it is deleted after successful validation.
