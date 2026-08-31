# Conversion workflow

MinerU Precision API v4 is the only extraction backend. Source originals remain outside the Obsidian vault.

## 1. Intake and routing

Identify the source file, course, document title, language, and any explicit profile. Resolve semester/course using [course-routing.md](course-routing.md). Confirm near-match course folders instead of silently creating a duplicate.

Reject a source that resolves inside the destination vault. Do not copy or move the original.

## 2. Profile and API options

Select or confirm `lecture-notes`, `policy-document`, or `paper` using [document-profiles.md](document-profiles.md). Validate extension and size without parsing the source locally. Confirm OCR for this document; never apply a hard-coded false default.

Load `obsidian-markdown` and `json-canvas`. Verify the encrypted token store, disclose the MinerU upload, then request only the encryption passphrase through a hidden prompt. On first setup, create encrypted state through `token-store.py`.

## 3. Staging and API extraction

Create staging outside the vault. Preserve the source hash. Request signed upload URLs, upload without forwarding Bearer/Content-Type, poll with the nested batch result path and backoff schedule, then safely download/extract the ZIP. Follow [mineru-api.md](mineru-api.md).

## 4. Page reconstruction

Prefer page-grouped `content_list_v2.json`. Otherwise group legacy blocks by `page_idx`. Apply [mineru-normalization.md](mineru-normalization.md): no global repeated anchor search, no blanket heading regex, explicit auxiliary-block inventory, and precise marker semantics.

## 5. Derived artifact generation

Create the document folder only after extraction/profile decisions are stable. Write:

- complete `<document-slug>.md`;
- derived `assets/` only;
- `<document-slug>.canvas` using evidence-based relationships;
- `conversion-report.md` from the fixed template.

## 6. Validation and delivery

Run `scripts/validate-output.py`, structural alignment checks, and [quality-gates.md](quality-gates.md). Move only validated derived artifacts from staging into the document folder. Report routing decisions, output paths, zero counts, review items, and not-checked gates.

## Failure behavior

- Missing/invalid encrypted token: configure or replace it through `token-store.py` without echo; otherwise stop.
- Upload declined or network unavailable: stop without local fallback.
- Unknown poll schema/state for 30 seconds: stop and show only a redacted key/type diagnostic.
- Poll timeout: report redacted batch reference and last per-file state; do not poll forever.
- Unsafe/malformed ZIP or implausibly empty output: stop before normalization.
- Ambiguous page order/heading: preserve structured blocks conservatively and record review.
- Existing document folder: use an explicit merge/overwrite decision.
- Validator failure: do not deliver as complete.
