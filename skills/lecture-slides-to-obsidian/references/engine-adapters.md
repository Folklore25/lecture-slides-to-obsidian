# Extraction backend adapter contract

No backend is selected or implemented in phase one. Use this reference when evaluating or adding one.

## Required capabilities

An adapter must expose enough information to normalize into the shared output contract:

- source page number for every block or asset;
- ordered text blocks with heading/list hints when available;
- image extraction or page rendering;
- explicit OCR behavior;
- equation and table output with warnings when confidence is low;
- deterministic output paths;
- backend name and version for the conversion report;
- non-zero exit status or structured failure when conversion is incomplete.

## Candidate routing model

- **Fast path:** digitally generated PDFs with simple reading order and little mathematical or spatial content.
- **Layout-aware path:** multi-column slides, dense diagrams, formulas, tables, mixed text and images, or pages whose reading order is not obvious.
- **OCR path:** scanned or raster-only pages.

These are capability classes, not product commitments. A future adapter may cover more than one class.

## Evaluation criteria

Measure page-order fidelity, heading/list recovery, equation accuracy, table structure, image association, language coverage, runtime, installation cost, offline behavior, licensing, and reproducibility. Prefer evidence from the repository's fixtures over broad claims.

## Integration rule

Backend-specific raw output must remain behind the adapter boundary. `SKILL.md`, the Obsidian note format, and golden tests should depend on the shared contract rather than a vendor-specific JSON schema.
