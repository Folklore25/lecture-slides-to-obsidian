# Quality gates

A conversion is complete only when the required gates pass, or the report marks an explicit failure or not-checked result.

## Decision gates

- Extraction mode was chosen explicitly: `native` or `mineru`.
- The user decided the note granularity. `preflight.py` emitted the `note_granularity` question and the answer is recorded in `resolved.note_granularity`.
- Native extraction ran on a model that can see the source pages (`checks.native_visual_input` is true).
- The conversion profile is one of `lecture-notes`, `policy-document`, `paper`.

## Routing and containment

- Semester ID/label and vault root are independently validated.
- Course matching is exact, or near-match candidates and the user's choice are recorded.
- The source resolves outside the Obsidian vault and remains unchanged.
- The document folder contains only derived Markdown, Canvas files, and assets. Every temporary file lives outside the vault.
- No dot-prefixed staging, tmp, cache, backup, or other workflow-owned path was created in the vault.

## Content-driven gates

- `note-plan.json` and `page-ledger.json` are final (`draft: false`) and equal the notes actually delivered.
- Every planned section exists as an H2 in its note, and no extra H2 exists except `## In-class notes`.
- No slide furniture survives as a heading or as body content: no agendas, dividers, course-admin blocks, exercise pages, page numbers, or repeated chrome.
- The page ledger accounts for every source page exactly once.
- Every kept or merged page carries an `evidence` phrase that literally occurs in its target note. `--extraction mineru` additionally checks per-page text recall; any exemption is declared in the ledger with a reason.
- Visual assets use lowercase semantic kebab-case names and every asset is referenced by a note embed or a Canvas file node.
- Comparison matrices and classification tables are real Markdown tables, not embedded screenshots, unless the visual itself carries unrecoverable meaning and the report says so.

## CLI and secret safety (MinerU mode only)

- The official `mineru-open-api extract` produced Markdown/assets/JSON; no direct HTTP, local parser, or lightweight fallback was used.
- The token reached only the CLI child environment as `MINERU_TOKEN`; CLI `--token`, `auth`, verbose HTTP logs, and `~/.mineru/config.yaml` were not used.
- Plaintext token, Authorization header, signed URLs, and secret-bearing responses are absent from registry, reports, logs, staging, output, and Git.
- Encrypted token state exists only at `state/mineru-api-token.enc.json`, has mode `0600`, passes HMAC verification, and uses the matching macOS Keychain wrapping key.

## MinerU transcription gates (only with `--extraction mineru`)

- Page reconstruction used V2 page groups or legacy `page_idx`, never global `md` anchors.
- Page markers are 1-based, monotonic, and precede the first included block from that page.
- Final visual assets follow `page-PPP-kind-NN.ext` and match the staging `asset-map.json`.
- `slide-layout-refiner` runs by default for `policy-document` and `paper`. Record `PASS` when it ran, `DISABLED` when `--no-visual-layout-refinement` was passed, `SKIPPED-VISUAL-INPUT` when the model cannot view the PDF, and `REJECTED` when it was rolled back. It is superseded and must not run for native extraction or for `lecture-notes`.

## Deterministic LaTeX normalization (optional)

- When enabled, `obsidian-latex-refiner` overwrites the note and its report passes conservation of visible non-math text, canonical math payloads, links, and assets. Page markers are preserved byte-identically when present; a marker-free note is one segment.
- Record `DISABLED` when off and `REJECTED` when rolled back.

## Pixel-level visual comparison — optional

Pixel-level visual diff against rendered source pages is not provided by this composition skill. Mark `NOT-CHECKED` unless a separate renderer was used and evidence is recorded. Never treat structural alignment as pixel-level PASS.

## Obsidian and Canvas

- `scripts/validate-output.py` passes.
- Every note has its required properties, exactly one H1, valid embeds, and one Canvas.
- The staging recall model accounts for every H2 section and contains no unsupported or generic relationship.
- The delegated Canvas aesthetic check passes with score at least 85, no hard errors, compact H3 concept cards, semantic color discipline, and acceptable edge routing.
- Canvas has one-minute recall, 2–7 learning modules, 4–20 traceable concept nodes, a connected selective semantic graph, synthesis, distinctions, and active-recall prompts.
- Local Obsidian DOM measurement was used to rebuild card heights; every text card retains the workstation profile's 8–12px effective headroom.
- The learning-module row was recomputed after DOM measurement and begins at least 80px below the final overview/source-lane bottom.
- Screenshot review was not used as the default renderer gate.
- Only memory-critical visuals are linked; exhaustive asset galleries are absent.
- Existing user-authored content was not overwritten without approval.
- The main Agent did not redraw or cosmetically modify the Canvas after the Canvas subagent's final SHA-bound checks.

## Completion language

Say “converted with a content-driven note structure and listed review items.” State the extraction mode, the granularity decision, and whether pixel-level rendering was not checked. Never claim lossless or perfect conversion.
