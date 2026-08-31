# Document profiles

The skill accepts course slides and other course documents. Select one profile before final normalization.

## Profile selection

There is no silent `lecture-notes` default. Use `preflight.py` and `auto-confirm`:

1. Before upload, infer from the user's description and filename, show the suggestion, and obtain a profile choice. A filename such as `Code of Conduct` should suggest `policy-document` even if the initial conversational wording said lecture notes.
2. After MinerU returns, use page-grouped blocks and layout metadata as a mismatch guard, not as the first profile decision.
3. Slide-like signals include short page-local blocks, repeated title/body patterns, presentation-sized pages, and frequent page-level headings.
4. Dense paragraphs, policy numbering, references, abstracts, or continuous prose signal a non-slide document.
5. If structured output contradicts the pre-upload choice, say so and reconfirm before writing to the vault; no second upload is required.

Do not stop merely because the input is not slides; use the appropriate profile.

## `lecture-notes`

- Preserve complete slide content in page order.
- Keep learning objectives, examples, diagrams, equations, and tables near their source pages.
- Add an `## In-class notes` section at the end.
- The canvas emphasizes learning objectives, concepts, dependencies, examples, and open questions.

## `policy-document`

- Preserve complete paragraphs, definitions, obligations, exceptions, and the source's explicit numbering.
- Do not demote headings with a blanket regex.
- Do not add `## In-class notes` unless the user asks.
- The canvas emphasizes scope, actors, rules, exceptions, enforcement, and cross-references.

## `paper`

- Preserve abstract, sections, methods, findings, limitations, references, and meaningful footnotes.
- Do not add `## In-class notes` unless the user asks.
- The canvas may adapt the critical-thinking pattern from `phd-deepread`: research question, argument, evidence, assumptions, methods, limitations, alternatives, and open questions.

## Source numbering

Preserve explicit source numbering in headings by default, including policy items such as `1. Do not plagiarize.` Numbers may carry cross-reference semantics and Markdown headings do not auto-number. Remove or relabel them only at the user's request.
