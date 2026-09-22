# Conversion workflow

An external source becomes content-driven Obsidian notes. Native multimodal reading is the default; the official `mineru-open-api` CLI is an optional aid. Source originals stay outside the vault.

## 1. Intake and routing

Run `scripts/preflight.py` early. Ask its questions in stages: vault root and course first; extraction mode, granularity, and profile next; language, OCR, and credential unlock only when MinerU is actually used.

Identify the source file, course, document title, and any explicit profile. Resolve semester/course with [course-routing.md](course-routing.md). Confirm near-match course folders instead of silently creating a duplicate. Reject a source that resolves inside the destination vault, and never copy or move the original.

## 2. Decisions before any writing

1. **Extraction.** Default to `native`. Choose `mineru` when the model wants machine-readable page groups, when the document is long or scanned, or when the user asks for it. Native mode requires a model that can see the pages; otherwise re-run with `--extraction mineru`.
2. **Granularity.** Ask the user every time: `single-note` or `section-notes`. Offer the rule of thumb (three or more independent sections and sixty or more source pages → `section-notes`). Never default it.
3. **Profile.** `lecture-notes`, `policy-document`, or `paper` via [document-profiles.md](document-profiles.md).

Load `obsidian-markdown` and `obsidian-canvas-designer` explicitly. Then run `scripts/token-store.py status` only if MinerU was selected.

## 3. Source reading

Read the source natively, page by page, before planning. On each page decide: substantive content, structural skeleton (agenda, divider, outline), furniture (title bar, logo, page number, footer), or administrative (welcome, staff, schedule, exercises).

This pass is what makes the output a note instead of a dump. Record what you saw; do not rely on a text layer to tell you what a page was for.

## 3b. Optional MinerU extraction

With `--extraction mineru`: create a uniquely named run directory under the system temporary directory (or the installed skill's non-hidden `tmp/`), outside the vault. Run `scripts/mineru-cli-adapter.py`; it unlocks the token, sets `MINERU_TOKEN`, calls `mineru-open-api extract -f md,json`, and writes page groups plus an asset map. Follow [mineru-cli.md](mineru-cli.md). Never call MinerU over raw HTTP and never parse the PDF locally.

## 4. Skeleton planning

Run `scripts/plan-note-structure.py`:

```text
# native reading
--page-count <pages> --profile <profile> --granularity <mode> --slug <slug> --title <title> \
  --output <run>/note-plan.json --ledger-output <run>/page-ledger.json

# MinerU aid
--page-groups <run>/<stem>.content-list-v2.compat.json ...
```

It writes a draft `note-plan.json` and `page-ledger.json`. With MinerU it also proposes sections from the document's own outline; with `--page-count` there is nothing to infer, so you author the sections yourself. Correct both files, then set `draft: false`. Re-validate with `--check-plan` and `--check-ledger`.

## 5. Note synthesis

Write one note per entry in the plan. Apply [obsidian-style.md](obsidian-style.md). Distil rather than transcribe: keep definitions, mechanisms, formulas, comparison tables, and decision rules; drop furniture. Convert matrices into real Markdown tables. Finish with `## In-class notes` for `lecture-notes`.

Extract only visuals whose structure matters and name them per [asset-naming.md](asset-naming.md). Record one `evidence` phrase per kept page in the ledger.

### Optional deterministic LaTeX normalization

Disabled by default. When enabled, load `obsidian-latex-refiner` and run `scripts/normalize-latex.py --target <note> --vault-root <root> --snapshot <run>/before.md --report <run>/latex-refinement-report.json`. It rewrites only math syntax, keeps visible text and links intact, treats a marker-free note as one segment, and restores the snapshot on any conservation failure. Delete the snapshot and report after success.

## 6. Derived artifacts

Write:

- the note or notes;
- a flat `assets/` directory referenced from the notes;
- one `<note-slug>.canvas` per note, delegated to `obsidian-canvas-designer`;
- staging `recall-model.json` per note after reading it;
- staging `canvas-aesthetic-check.json`, `canvas-render-metrics.json`, and `canvas-render-check.json` per Canvas;
- a temporary `conversion-report.md` under staging for Agent QA only.

## 7. Validation and delivery

Require the Canvas subagent to return PASS plus aesthetic, measurement, and final DOM-check files. Then run `scripts/validate-output.py` with the plan, the ledger, and, in MinerU mode, the page groups. Read [validation.md](validation.md) and [quality-gates.md](quality-gates.md).

Extract routing decisions, output paths, extraction mode, granularity, zero counts, review items, and not-checked gates for the final response; then delete the temporary report, recall model, plan, ledger, page groups, and Canvas QA files. Never place QA files in the vault.

## Failure behavior

- Missing/invalid encrypted token in MinerU mode: configure or replace it through `token-store.py` without echo; otherwise stop.
- Missing CLI, CLI authentication/network/timeout error, or incomplete md/json output: report the redacted CLI error and stop without direct HTTP or local fallback.
- No multimodal capability but native extraction selected: stop and ask, or re-run with `--extraction mineru`.
- Ambiguous page order or heading: preserve structured blocks conservatively and record a review item.
- Existing document folder: use an explicit merge/overwrite decision.
- Validator failure: do not deliver as complete.
