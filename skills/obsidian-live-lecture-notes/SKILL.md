---
name: obsidian-live-lecture-notes
description: Capture a learner's live classroom thoughts from chat and insert them non-destructively into the corresponding sections of an open Obsidian course note. Use during class when complete Markdown already exists; do not transcribe slides, process ASR, or rewrite source content.
metadata:
  required-skills: "obsidian-markdown, obsidian-cli"
---

# Obsidian Live Lecture Notes

Keep the learner focused on the lecture: accept short thoughts in chat, route each thought to the best existing section, and insert a clearly separated in-class callout without rewriting the course-material transcription.

## Bind the note once

Because the Obsidian terminal may be the active leaf, do not trust the active file implicitly. At the start of a classroom session:

1. Load `obsidian-markdown` and `obsidian-cli`.
2. List open Markdown leaves through Obsidian CLI `eval` and obtain their vault-relative paths.
3. If one open note has `type: course-material`, bind it for this chat. If several qualify, ask once for the exact note.
4. Keep the binding in conversation state. Do not create a user-level session file.

## Route each thought

1. Read the bound note outline and the minimum surrounding text needed for semantic routing.
2. Choose one exact existing H2 or H3 only when the match is unique and confident.
3. If ambiguous, route to the exact `## In-class notes` section with `routing_status: unresolved`; do not interrupt the lecture with a long clarification loop.
4. Create one patch entry following [references/insertion-contract.md](references/insertion-contract.md).
5. Run `scripts/apply-note-patches.py --backend obsidian-cli`; never perform an unconstrained whole-note rewrite.
6. Reply briefly with the destination heading and captured idea. Keep analysis out of the classroom chat unless asked.

## Non-negotiable boundaries

- Treat the learner's wording as their thought. Preserve meaning and first-person stance; only repair obvious speech-to-text fragments when necessary.
- Insert, never replace, source transcription or page markers.
- Do not promote headings, restructure the note, create concepts the learner did not express, or silently resolve an ambiguous destination.
- A thought may be a connection, question, interpretation, example, disagreement, hypothesis, or action item. Do not force every thought into a summary.
- Stable entry IDs make retries idempotent. Never duplicate an already applied entry.
- This skill does not process teacher ASR transcripts. Use `lecture-asr-enricher` after class.

## Resources

- Read [references/live-workflow.md](references/live-workflow.md) before starting a session.
- Read [references/insertion-contract.md](references/insertion-contract.md) before creating a patch.
- Use [templates/live-note-patch.example.json](templates/live-note-patch.example.json) as a schema example, not as course content.
