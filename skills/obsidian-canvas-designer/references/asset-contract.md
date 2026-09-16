# Canvas asset contract

The Canvas designer accepts existing derived visual assets. It does not extract, rename, or import them.

- Asset paths are document-relative and start with `assets/`.
- Content-driven notes use lowercase semantic kebab-case names: `assets/qualitative-research-cycle.png`.
- MinerU transcription folders keep `assets/page-<PPP>-<figure|table|equation|chart|fallback>-<NN>.<ext>`.
- Resolve every file under the document's `assets/` directory and reject absolute paths, `..`, missing files, source originals, or staging paths.
- Select at most six visuals whose structure materially improves recall.
- Attach each selected visual to the concept it explains; never build an exhaustive image gallery.
- Keep the original document outside the Canvas and vault artifact folder.
