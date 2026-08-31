# Conversion workflow

Use this process when performing a real conversion. MinerU Precision API v4 is the only extraction backend.

## 1. Intake

Identify the source PDF, course name or code, lecture label, and language hints. Resolve the course using the persistent registry and [course-routing.md](course-routing.md). For an unmatched course, collect and persist the semester root before continuing. Tell the user that extraction uploads the file to MinerU. Never infer permission to overwrite an existing note.

## 2. Preflight

Validate the file extension and size against [mineru-api.md](mineru-api.md). Select `language`, OCR, formula, table, and page-range options from known course/user context without parsing the PDF locally. Load `obsidian-markdown`, then collect the plaintext API token with the required disclosure.

## 3. Staging

Create a dedicated working directory outside the final vault path. Preserve the original PDF byte-for-byte. Store downloaded API output separately from normalized output so failures remain diagnosable. Never store the token or signed URLs.

## 4. API extraction

Request signed upload URLs, upload the PDF without the Bearer header, poll the batch result, download the result ZIP, and safely extract it in staging. Preserve `full.md`, images, JSON, page boundaries, API state, and warnings. Do not run a local PDF parser.

## 5. Normalization

Transform raw output into the shared output contract. Repair obvious mechanical issues only when the evidence is clear. Keep page provenance, use relative asset links, and add visual fallback for complex or uncertain pages.

## 6. Validation

Run the quality gates. Compare a representative selection of opening, middle, and ending pages, plus every flagged page, against the PDF. Validate Markdown links and asset existence.

## 7. Delivery

Copy or move only validated final artifacts into the registered course destinations. Copy the source PDF to the registered slides folder without deleting the original. Report the matched semester/course, classified paths, fallback pages, unresolved uncertainty, and whether manual review is required.

## Failure behavior

- If no suitable backend is available, stop and name the missing capability.
- If the API token is absent, invalid, or expired, stop or request one replacement according to the API contract; never print the token.
- If upload disclosure is declined, stop without sending the file.
- If polling times out, report the non-secret batch reference and current state rather than treating the task as failed or polling forever.
- If the result archive is unsafe, incomplete, or malformed, stop before normalization.
- If extraction produces empty or implausibly short output, do not generate a confident-looking note.
- If a page's reading order is ambiguous, preserve blocks conservatively and include the page image.
- If the destination already exists, create a distinct candidate or request overwrite approval.
- If course matching is ambiguous or the registered root is stale, stop before conversion and repair the mapping.
- Keep partial output in staging until the user decides whether it is useful.
