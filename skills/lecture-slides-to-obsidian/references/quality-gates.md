# Quality gates

A conversion is complete only when required gates pass or the report marks an explicit failure/not-checked result.

## Routing and containment

- Semester ID/label and vault root are independently validated.
- Course matching is exact, or near-match candidates and the user's choice are recorded.
- The source resolves outside the Obsidian vault and remains unchanged.
- The document folder contains only derived Markdown, Canvas, and assets; the temporary report, recall model, and DOM render-QA files are outside the vault.

## CLI and secret safety

- Official `mineru-open-api extract` produced Markdown/assets and JSON; no direct HTTP/local/lightweight fallback was used.
- Token reached only the CLI child environment as `MINERU_TOKEN`; CLI `--token`, `auth`, verbose HTTP logs, and `~/.mineru/config.yaml` were not used.
- Plaintext token, Authorization header, signed URLs, and secret-bearing responses are absent from registry, reports, logs, staging, output, and Git.
- Encrypted token state exists only at `state/mineru-api-token.enc.json`, has mode `0600`, passes HMAC verification, has no plaintext token substring, and uses the matching macOS Keychain wrapping key.
- ZIP path/type/count/size safety checks passed.

## Structural alignment — required

- Page reconstruction used V2 page groups or legacy `page_idx`, not global `full.md` anchors.
- Page markers are 1-based, monotonic, and precede the first included block from that page.
- Heading levels use structured MinerU signals plus series/context consistency; source numbering is preserved.
- Auxiliary headers/footers/footnotes are inventoried and omissions documented.
- Figures, tables, equations, and fallback pages are counted, including zeros.
- Final visual assets follow the deterministic `page-PPP-kind-NN.ext` contract and match staging `asset-map.json`.
- When multimodal layout refinement is enabled, its report passes frontmatter, immutable marker-line, page-local token order, link, and per-page asset conservation. When disabled, record `DISABLED`; when rejected, preserve the base Markdown and record `REJECTED`.

## Pixel-level visual comparison — optional

Pixel-level visual diff against rendered source pages is not provided by this composition skill. Mark `NOT-CHECKED` unless a separate renderer was explicitly used and evidence is recorded. Never treat structural alignment as pixel-level PASS.

## Obsidian and Canvas

- `scripts/validate-output.py` passes.
- Complete Markdown has required properties, one H1, valid markers, and resolving assets.
- The staging recall model accounts for every H2 section and contains no unsupported/generic relationship.
- The delegated Canvas aesthetic check passes with score at least 85, no hard errors, compact H3 concept cards, semantic color discipline, and acceptable edge routing.
- Canvas has one-minute recall, 2–7 learning modules, 4–20 traceable concept nodes, a connected selective semantic graph, synthesis, distinctions, and active-recall prompts.
- Canvas JSON, IDs, meaningful edge labels, paths, density, and non-overlap checks pass.
- Local Obsidian DOM measurement was used to rebuild card heights; every text card retains the workstation profile's 8px safety margin before grid rounding.
- Reading viewport is `zoom = 0`, giving a 16px effective Canvas font against the local 13px sidebar reference. Fit-all zoom is not a body-text readability gate.
- Screenshot review was not used as the default renderer gate.
- Only memory-critical visuals are linked; decorative or exhaustive asset galleries are absent.
- Existing user-authored content was not overwritten without approval.
- The main Agent did not redraw or cosmetically modify the Canvas after the Canvas subagent's final SHA-bound checks.

## Completion language

Say “converted with structural checks and listed review items.” State whether pixel-level rendering was not checked. Never claim lossless/perfect conversion.
