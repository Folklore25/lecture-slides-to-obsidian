# Conversion workflow

The official `mineru-open-api` precision CLI is the extraction client. Source originals remain outside the Obsidian vault.

## 1. Intake and routing

Run `scripts/preflight.py` early. Ask its questions in stages: vault root and course first; profile next; language/OCR and credential unlock only when upload is ready. Identify the source file, course, document title, language, and any explicit profile. Resolve semester/course using [course-routing.md](course-routing.md). Confirm near-match course folders instead of silently creating a duplicate.

Reject a source that resolves inside the destination vault. Do not copy or move the original.

## 2. Profile and API options

Select or confirm `lecture-notes`, `policy-document`, or `paper` using filename/user context before upload. A name such as `example-policy.pdf` should trigger a `policy-document` suggestion immediately. Validate extension and size without parsing the source locally. Infer then confirm the MinerU language enum and confirm an OCR boolean; neither field has a request default.

Load `obsidian-markdown`, `json-canvas`, and `obsidian-cli`. Verify the local render profile, encrypted token file, and Keychain wrapping key. On first setup, store the chat-provided token through `token-store.py set --token-stdin`; later runs unlock automatically without another conversational prompt.

## 3. Staging and official CLI extraction

Create staging outside the vault and preserve the source hash. Run `scripts/mineru-cli-adapter.py`; it unlocks the token, sets `MINERU_TOKEN`, and delegates upload/poll/download to `mineru-open-api extract -f md,json`. Follow [mineru-cli.md](mineru-cli.md). Do not call MinerU HTTP endpoints directly.

## 4. Page reconstruction

Prefer page-grouped `content_list_v2.json`. Otherwise group legacy blocks by `page_idx`. Apply [mineru-normalization.md](mineru-normalization.md): no global repeated anchor search, no blanket heading regex, explicit auxiliary-block inventory, and precise marker semantics.

## 5. Derived artifact generation

Create the document folder only after extraction/profile decisions are stable. Write:

- complete `<document-slug>.md`;
- derived `assets/` only;
- staging `recall-model.json` after reading the complete Markdown;
- `<document-slug>.canvas` as a knowledge-recall map rendered from that semantic model;
- staging `canvas-render-metrics.json` and `canvas-render-check.json` from local Obsidian DOM QA;
- a temporary `conversion-report.md` under staging for Agent QA only.

## 6. Validation and delivery

Measure the first Canvas with `canvas-render-qa.py`, rebuild with its measurements, and run the final DOM check. Then run `scripts/validate-output.py` with all staging QA files, structural alignment checks, and [quality-gates.md](quality-gates.md). Move only validated Markdown/Canvas/assets into the document folder. Extract routing decisions, output paths, zero counts, review items, and not-checked gates for the final response; then delete the temporary report, recall model, render metrics, and render check before sending that response.

## Failure behavior

- Missing/invalid encrypted token: configure or replace it through `token-store.py` without echo; otherwise stop.
- Missing CLI, CLI authentication/network/timeout error, or incomplete md/json output: report the redacted CLI error and stop without direct HTTP/local fallback.
- Ambiguous page order/heading: preserve structured blocks conservatively and record review.
- Existing document folder: use an explicit merge/overwrite decision.
- Validator failure: do not deliver as complete.
