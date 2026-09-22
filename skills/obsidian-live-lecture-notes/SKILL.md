---
name: obsidian-live-lecture-notes
description: Capture a learner's live classroom thoughts from chat and insert them non-destructively into the corresponding sections of an open Obsidian course note. Use during class when complete Markdown already exists; do not transcribe slides, process ASR, or rewrite source content.
metadata:
  required-skills: "obsidian-markdown"
---

# Obsidian Live Lecture Notes

Keep the learner focused on the lecture: accept short thoughts in chat, route each thought to the best existing section, and insert a clearly separated in-class callout without rewriting the course-material transcription.

## Bind the note once

Because the Obsidian terminal may be the active leaf, do not trust the active file implicitly. At the start of a classroom session:

1. Load `obsidian-markdown`. Note and vault writes go through the filesystem backend.

**Never run the Obsidian CLI while Obsidian is not running.** This is the one hard rule. With the app up, CLI calls talk to it and do not steal focus, so ordinary use is fine. With the app down, the CLI cold-starts Obsidian: the window pops to the front, the app checks for updates, and the command **never returns** — measured, three commands produced three launches and three window pop-outs. So check that the app is running before any CLI call, bound every call with a timeout, and never let a CLI call be the thing that launches Obsidian.
2. Take the target note path from the caller or the open document, and read it directly from disk. Do not enumerate open leaves through Obsidian.
3. If one open note has `type: course-material`, bind it for this chat. If several qualify, ask once for the exact note.
4. Keep the binding in conversation state. Do not create a user-level session file.

## Route each thought

1. Read the bound note outline and the minimum surrounding text needed for semantic routing.
2. Choose one exact existing H2 or H3 only when the match is unique and confident.
3. If ambiguous, route to the exact `## In-class notes` section with `routing_status: unresolved`; do not interrupt the lecture with a long clarification loop.
4. Create one patch entry following [references/insertion-contract.md](references/insertion-contract.md).
5. Run `scripts/apply-note-patches.py --backend fs`; never perform an unconstrained whole-note rewrite.
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
