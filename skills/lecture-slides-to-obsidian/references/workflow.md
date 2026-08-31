# Conversion workflow

Use this process when performing a real conversion. The exact backend may vary, but the artifact boundaries and failure behavior should remain stable.

## 1. Intake

Identify the source PDF, course name or code, lecture label, and language hints. Resolve the course using the persistent registry and [course-routing.md](course-routing.md). For an unmatched course, collect and persist the semester root before continuing. Never infer permission to upload the file or overwrite an existing note.

## 2. Preflight

Inspect page count, whether text is selectable, dominant languages, rotation, image-only pages, and signs of multi-column or slide-style layout. Inventory the available local extraction tools. Choose a backend only after this inspection.

## 3. Staging

Create a dedicated working directory outside the final vault path. Preserve the original PDF byte-for-byte. Store raw extraction output separately from normalized output so failures remain diagnosable.

## 4. Extraction

Capture page boundaries and source page numbers. Extract text blocks, lists, tables, equations, captions, and images without silently changing uncertain content. Record confidence or warnings when the backend exposes them.

## 5. Normalization

Transform raw output into the shared output contract. Repair obvious mechanical issues only when the evidence is clear. Keep page provenance, use relative asset links, and add visual fallback for complex or uncertain pages.

## 6. Validation

Run the quality gates. Compare a representative selection of opening, middle, and ending pages, plus every flagged page, against the PDF. Validate Markdown links and asset existence.

## 7. Delivery

Copy or move only validated final artifacts into the registered course destinations. Copy the source PDF to the registered slides folder without deleting the original. Report the matched semester/course, classified paths, fallback pages, unresolved uncertainty, and whether manual review is required.

## Failure behavior

- If no suitable backend is available, stop and name the missing capability.
- If extraction produces empty or implausibly short output, do not generate a confident-looking note.
- If a page's reading order is ambiguous, preserve blocks conservatively and include the page image.
- If the destination already exists, create a distinct candidate or request overwrite approval.
- If course matching is ambiguous or the registered root is stale, stop before conversion and repair the mapping.
- Keep partial output in staging until the user decides whether it is useful.
