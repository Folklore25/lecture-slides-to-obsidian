# Conversion workflow

MinerU Precision API v4 is the only extraction backend. Source originals remain outside the Obsidian vault.

## 1. Intake and routing

Run `scripts/preflight.py` early. Ask its questions in stages: vault root and course first; profile next; language/OCR and credential unlock only when upload is ready. Identify the source file, course, document title, language, and any explicit profile. Resolve semester/course using [course-routing.md](course-routing.md). Confirm near-match course folders instead of silently creating a duplicate.

Reject a source that resolves inside the destination vault. Do not copy or move the original.

## 2. Profile and API options

Select or confirm `lecture-notes`, `policy-document`, or `paper` using filename/user context before upload. A name such as `example-policy.pdf` should trigger a `policy-document` suggestion immediately. Validate extension and size without parsing the source locally. Infer then confirm the MinerU language enum and confirm an OCR boolean; neither field has a request default.

Load `obsidian-markdown` and `json-canvas`. Verify the encrypted token file and Keychain wrapping key. On first setup, store the chat-provided token through `token-store.py set --token-stdin`; later runs unlock automatically without another conversational prompt.

## 3. Staging and API extraction

Create staging outside the vault. Preserve the source hash. Request signed upload URLs, upload without forwarding Bearer/Content-Type, poll with the nested batch result path and backoff schedule, then safely download/extract the ZIP. Follow [mineru-api.md](mineru-api.md).

## 4. Page reconstruction

Prefer page-grouped `content_list_v2.json`. Otherwise group legacy blocks by `page_idx`. Apply [mineru-normalization.md](mineru-normalization.md): no global repeated anchor search, no blanket heading regex, explicit auxiliary-block inventory, and precise marker semantics.

## 5. Derived artifact generation

Create the document folder only after extraction/profile decisions are stable. Write:

- complete `<document-slug>.md`;
- derived `assets/` only;
- `<document-slug>.canvas` using evidence-based relationships;
- a temporary `conversion-report.md` under staging for Agent QA only.

## 6. Validation and delivery

Run `scripts/validate-output.py` with the staging report, structural alignment checks, and [quality-gates.md](quality-gates.md). Move only validated Markdown/Canvas/assets into the document folder. Extract routing decisions, output paths, zero counts, review items, and not-checked gates for the final response; then delete the temporary report and send that response.

## Failure behavior

- Missing/invalid encrypted token: configure or replace it through `token-store.py` without echo; otherwise stop.
- Upload declined or network unavailable: stop without local fallback.
- Unknown poll schema/state for 30 seconds: stop and show only a redacted key/type diagnostic.
- Poll timeout: report redacted batch reference and last per-file state; do not poll forever.
- Unsafe/malformed ZIP or implausibly empty output: stop before normalization.
- Ambiguous page order/heading: preserve structured blocks conservatively and record review.
- Existing document folder: use an explicit merge/overwrite decision.
- Validator failure: do not deliver as complete.
