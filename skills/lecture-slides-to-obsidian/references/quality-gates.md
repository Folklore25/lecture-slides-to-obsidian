# Quality gates

A conversion is complete only when required gates pass or the report marks an explicit failure/not-checked result.

## Routing and containment

- Semester ID/label and vault root are independently validated.
- Course matching is exact, or near-match candidates and the user's choice are recorded.
- The source resolves outside the Obsidian vault and remains unchanged.
- The document folder contains only derived Markdown, Canvas, and assets; the temporary report is outside the vault.

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

## Pixel-level visual comparison — optional

Pixel-level visual diff against rendered source pages is not provided by this composition skill. Mark `NOT-CHECKED` unless a separate renderer was explicitly used and evidence is recorded. Never treat structural alignment as pixel-level PASS.

## Obsidian and Canvas

- `scripts/validate-output.py` passes.
- Complete Markdown has required properties, one H1, valid markers, and resolving assets.
- Canvas JSON, IDs, edges, paths, and non-overlap checks pass.
- Existing user-authored content was not overwritten without approval.

## Completion language

Say “converted with structural checks and listed review items.” State whether pixel-level rendering was not checked. Never claim lossless/perfect conversion.
