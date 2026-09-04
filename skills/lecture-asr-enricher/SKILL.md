---
name: lecture-asr-enricher
description: Compare a post-class teacher ASR Markdown transcript with an existing Obsidian course note, identify genuinely new teaching context, and insert source-anchored lecturer additions into the corresponding sections. Use after class when both Markdown inputs already exist; do not run ASR or rewrite slide transcription.
metadata:
  required-skills: "obsidian-markdown, obsidian-live-lecture-notes"
---

# Lecture ASR Enricher

Enrich an existing course-material note with the lecturer's added explanations, examples, emphasis, corrections, boundary conditions, Q&A, and actionable logistics from an ASR Markdown transcript.

## Inputs

- exact target course-note path;
- teacher ASR transcript as Markdown, with timestamps or stable headings when available;
- vault root;
- staging directory for the enrichment plan and apply patch.

The transcript may be inside or outside the vault. It is evidence, not a replacement note.

## Workflow

1. Load `obsidian-markdown` and `obsidian-live-lecture-notes`. This post-class task drives the shared apply script from the filesystem; it does not load or use Obsidian CLI.
2. Read the complete course note and ASR transcript. Inventory exact target H2/H3 headings.
3. Apply [references/novelty-policy.md](references/novelty-policy.md): discard repetition and filler; retain only source-supported additions.
4. Write `enrichment-plan.json` following [references/enrichment-plan.md](references/enrichment-plan.md).
5. Run `scripts/validate-enrichment-plan.py --output-patch <staging>/teacher-note-patch.json`.
6. Review low-confidence/rejected entries without applying them. If no genuine additions remain, report that clearly and leave the note unchanged.
7. Apply accepted entries with the sibling [apply-note-patches.py](../obsidian-live-lecture-notes/scripts/apply-note-patches.py) using the filesystem backend: `--backend fs --vault-root <vault-root> --patch <staging>/teacher-note-patch.json`. Do not read or write the note through Obsidian CLI.
8. Re-read the note file directly from the vault and confirm every teacher marker exists exactly once. The apply script already verifies its filesystem write via SHA readback; this is a final marker sanity check, not an Obsidian CLI read. After a successful summary, delete the temporary plan/apply patch; do not delete the ASR source.

## Non-negotiable boundaries

- Paraphrase by default. Preserve a short exact phrase only when wording itself is pedagogically important.
- Never convert ASR uncertainty into a confident fact. Keep names, numbers, formulas, and corrections conservative.
- Do not reinsert slide text merely because the lecturer repeated it.
- Do not merge teacher additions into the source transcription paragraphs. Keep lecturer callouts visibly separate from student thoughts and slide content.
- Do not remove or rewrite `lecture-layer:student` blocks.
- The apply tool only inserts complete blocks under exact existing H2/H3 headings.

## Resources

- Read [references/novelty-policy.md](references/novelty-policy.md) before semantic comparison.
- Read [references/enrichment-plan.md](references/enrichment-plan.md) before writing staging JSON.
- Use [templates/enrichment-plan.example.json](templates/enrichment-plan.example.json) only as a schema example.
