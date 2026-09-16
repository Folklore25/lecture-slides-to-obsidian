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
- Triage ran visual-first: every page declares `visual: true|false`, and no page was dropped for a text-based reason while carrying a figure.
- Pages whose teaching signal is a figure used `evidence_asset` rather than being forced into a prose quote or dropped.
- Every meaningful source visual is extracted, named, and embedded at its point of use. No visual was reduced to a prose description and discarded.
- The page ledger declares a visual disposition for every kept or merged page: kept with an asset name, or dropped with a controlled reason. `superseded-by-table` additionally states `rendered_as`.
- No asset is a degenerate crop: every extracted visual has both sides at least `40px` and an aspect ratio at or below `8:1`.
- Source tables appear as Markdown tables and source equations appear as LaTeX, with any exception carrying a stated reason in the ledger.
- No bullet, table row, or fact was added that the source does not contain; where the source is itself incomplete, a review item records the gap.
- Repeated template chrome is classified by the planner's footprint detection and lands as `repeated-chrome` rather than being re-decided page by page. Logos, watermarks, template ornaments, and footer art never reach `assets/`.
- Every asset listed as kept in the ledger exists under `assets/` and is referenced by a note embed or a Canvas file node, and every file in `assets/` is listed in the ledger.

## CLI and secret safety (MinerU mode only)

- The official `mineru-open-api extract` produced Markdown/assets/JSON; no direct HTTP, local parser, or lightweight fallback was used.
- The token reached only the CLI child environment as `MINERU_TOKEN`; CLI `--token`, `auth`, verbose HTTP logs, and `~/.mineru/config.yaml` were not used.
- Plaintext token, Authorization header, signed URLs, and secret-bearing responses are absent from registry, reports, logs, staging, output, and Git.
- Encrypted token state exists only at `state/mineru-api-token.enc.json`, has mode `0600`, passes HMAC verification, and uses the matching macOS Keychain wrapping key.

## Batch dispatch and the Canvas lane

- With two or more source files, one subagent task was created per file, and `scripts/plan-conversion-batch.py` verified their isolation.
- Course routing, the registry, and slug decisions were resolved once by the main Agent before dispatch; no two workers wrote shared state.
- Each file had its own document folder and its own staging directory.
- Every DOM measurement ran under the shared GUI lease, no two measurements overlapped, and no agent activated or foregrounded the Obsidian window. Window focus was recorded as a diagnostic, not required.
- Every Canvas kept its own recall model, Canvas path, aesthetic check, render metrics, and render check.
- Per-file status was reported; no partial batch was collapsed into a single PASS.

## MinerU transcription gates (only with `--extraction mineru`)

- Page reconstruction used V2 page groups or legacy `page_idx`, never global `md` anchors.
- Page markers are 1-based, monotonic, and precede the first included block from that page.
- Final visual assets follow `page-PPP-kind-NN.ext` and match the staging `asset-map.json`.

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
