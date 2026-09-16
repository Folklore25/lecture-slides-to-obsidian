# Document profiles

The skill accepts course slides and other course documents. Select one profile before writing notes.

## Extraction mode is separate from profile

`--extraction` decides where the text comes from; the profile decides what the note must contain.

- `native` (default): the multimodal model reads the source itself. Works for every profile, produces no page markers.
- `mineru`: the official CLI produces structured page groups. Used as an aid for lecture-notes, or as the faithful-transcription source for `policy-document` and `paper`, where page markers are kept.

## Profile selection

Use `preflight.py`. Infer from the user's description and filename, show the suggestion, and obtain a choice. Do not stop merely because the input is not slides.

Slide-like signals: short page-local blocks, repeated title/body patterns, presentation-sized pages, frequent page-level headings.
Non-slide signals: dense paragraphs, policy numbering, references, abstracts, continuous prose.

## `lecture-notes`

Content-driven topic notes. **This profile is a synthesis task, not a transcription task.**

**Page triage starts from "is there a visual?", not from "is there enough text?"** A slide with 60 characters of extractable text and one embedded figure is a content page: a business framing, a worked example, an in-class quiz. Text-based triage reads it as empty and drops it, and the pages it eats are the deck's most teachable ones. Ask the visual question first, answer it per page in the ledger, and only then consider dropping.

- The note's H2 headings are the source document's own sections, never slide titles, slide numbers, or page furniture.
- Choose `single-note` (one note, sections as H2) or `section-notes` (one note per source section) with the user, on every conversion. Rule of thumb to offer: three or more independent sections *and* sixty or more source pages → suggest `section-notes`; otherwise suggest `single-note`.
- **Section notes keep source order in their filenames.** Every slug is `<document-slug>-<NN>-<section-slug>`, numbered from `01`. A plain filename sort must reproduce the order of the source document, because that listing is what a learner browses. `scripts/plan-note-structure.py` drafts these slugs, and the plan contract rejects a section note whose slug has no ordinal, whose ordinals are not contiguous `01..NN`, or whose notes are not listed in ascending source-page order.
- Keep what a learner needs to reconstruct the lesson: definitions, mechanisms, causal chains, formulas, comparison matrices, decision rules, worked-example logic, stated limitations, and cited sources.
- Drop agendas, section dividers, course-admin or welcome pages, exercise and quiz pages, repeated title/logo/footer chrome, decorative slides, and duplicated summaries. Mark each in the page ledger as `dropped` with a controlled reason.
- **A page whose content is a figure or a wide data table is a content page, not furniture.** Slides that are one picture plus a short caption have almost no text, so any text-based triage reads them as empty; in practice that is how worked examples, data tables, and whole concepts go missing. Resolve each such page explicitly: keep it and extract the figure, or drop it for a visual-aware reason (`duplicate`, `repeated-chrome`, `illegible`). `non-substantive`, `section-divider`, and `agenda` assert that a page had no content and are rejected for a page that carries a detected visual.\n- **Extract and embed every meaningful visual at the position where it belongs.** Never describe a diagram, chart, matrix, or annotated figure in prose and then drop it.
- A prose description may accompany a visual, never replace it.
- A Markdown table replaces a visual only when the text carries exactly the same information, which in practice means a legible numeric data table. Declare that in the page ledger as `superseded-by-table`.
- Record every visual decision per page: kept with an asset name, or dropped with a controlled reason.
- Record one `evidence` phrase per kept page: a short quotation that actually appears in the delivered note.
- **Never add a fact, table row, or bullet the source does not contain.** Decks are often themselves incomplete: a slide promising three items and listing two, a table with placeholder cells. Record a review item for that gap instead of quietly completing it, so a reader can tell what came from the lecturer.
- Keep `## In-class notes` at the end when the learner will take notes in class.
- The Canvas reconstructs the lesson through foundations, mechanisms/processes, applications/evidence, boundaries/misconceptions, and active-recall questions, following conceptual dependency rather than page order.

## `policy-document`

- Preserve complete paragraphs, definitions, obligations, exceptions, and the source's explicit numbering.
- Do not demote headings with a blanket regex.
- Do not add `## In-class notes` unless the user asks.
- With `--extraction mineru`, page markers and `page-PPP-kind-NN.ext` assets stay in force.
- The Canvas reconstructs scope → actors → rules/obligations → exceptions → enforcement.

## `paper`

- Preserve abstract, sections, methods, findings, limitations, references, and meaningful footnotes.
- Do not add `## In-class notes` unless the user asks.
- With `--extraction mineru`, page markers and `page-PPP-kind-NN.ext` assets stay in force.
- The Canvas adapts the critical-thinking pattern from `phd-deepread`: research question, argument, evidence, assumptions, methods, limitations, alternatives, open questions.

## Source numbering

Preserve explicit source numbering in headings by default, including policy items such as `1. Do not plagiarize.` Numbers carry cross-reference semantics. Remove or relabel them only at the user's request.
