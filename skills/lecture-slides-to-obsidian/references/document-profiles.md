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

- The note's H2 headings are the source document's own sections, never slide titles, slide numbers, or page furniture.
- Choose `single-note` (one note, sections as H2) or `section-notes` (one note per source section) with the user, on every conversion. Rule of thumb to offer: three or more independent sections *and* sixty or more source pages → suggest `section-notes`; otherwise suggest `single-note`.
- Keep what a learner needs to reconstruct the lesson: definitions, mechanisms, causal chains, formulas, comparison matrices, decision rules, worked-example logic, stated limitations, and cited sources.
- Drop agendas, section dividers, course-admin or welcome pages, exercise and quiz pages, repeated title/logo/footer chrome, decorative slides, and duplicated summaries. Mark each in the page ledger as `dropped` with a controlled reason.
- Convert comparison matrices and classification tables into real Markdown tables. Keep an image only when the visual itself carries meaning that prose cannot carry.
- Record one `evidence` phrase per kept page: a short quotation that actually appears in the delivered note.
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
