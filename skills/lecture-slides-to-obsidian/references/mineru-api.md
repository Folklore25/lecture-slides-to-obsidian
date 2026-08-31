# MinerU Precision API v4

Canonical documentation: <https://mineru.net/apiManage/docs>

This is the only PDF extraction backend for the skill. Local parsing, local MinerU models/CLI, third-party MinerU wrappers, and the unauthenticated lightweight Agent API are out of scope.

## Limits and defaults

- Maximum file size: 200 MB.
- Maximum document length: 200 pages.
- Maximum upload URLs requested at once: 50.
- Signed upload URLs are valid for 24 hours.
- Default `model_version`: `vlm`.
- Default `language`: `ch` for mixed Chinese/English slides.
- Formula and table recognition are enabled. OCR has no hard-coded default: confirm `is_ocr` for every document. Recommend true when the user identifies a scan, image-only document, or unreliable existing OCR; otherwise explain the tradeoff and ask.

## Plaintext token collection

Collect the API token from the Agent's interactive input only after course routing, file validation, and upload disclosure are complete. Use this prompt or an equivalent concise warning:

```text
这份课件将上传到 MinerU 官方 API。请在输入框粘贴本次使用的 API token。token 会以明文进入当前会话，可能由当前 Agent 宿主保留；我不会回显、写入文件、注册表、配置、日志或报告。
```

Treat the token as session-only:

- do not repeat or quote any part of it;
- do not persist it in `state/`, configuration, environment profiles, shell history, temporary files, reports, or Git;
- do not include it directly in a command line or diagnostic output;
- send `Authorization: Bearer <token>` only to HTTPS requests whose origin is exactly `https://mineru.net`;
- on `A0202` or `A0211`, discard it and ask once for a replacement without showing the rejected value.

The conversation host may retain the plaintext user message. Do not promise deletion that the Agent cannot verify.

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

This example assumes the user explicitly chose `is_ocr: false`; it is not a default.

Do not use `POST /api/v4/extract/task` for a local file; that endpoint accepts a remotely accessible file URL and does not directly upload the file.

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

Preserve the raw API artifacts, including `full.md`, images, `content_list.json`, and other JSON when present. Never treat a successful archive download as proof that every page was parsed correctly.

## Secret-safe reporting

The conversion report may contain the provider (`MinerU Precision API v4`), model, non-secret options, result state, and redacted task/batch reference. It must not contain the API token, Authorization header, signed upload URL, full result URL, or raw response headers.
