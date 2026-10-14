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

### 3a. Render the pages to read

`pi.read` cannot open a PDF, and a page rasterised at 150 DPI is a ~1 MB PNG that the harness inlines as base64: 1.4 MB of request body per page, 29 MB for a 34-page deck. That is what makes a gateway answer 413 before the model ever sees a page.

So render once, properly, with the bundled script. First run of a deck, ask for the first batch:

```text
scripts/render-source-pages.py <source.pdf> --output-dir <run>/pages \
  --pages 1-8 --report <run>/page-render.json
```

Each page comes back as `page-<PPP>.webp`, encoded at the resolution the model will actually receive and never larger than the harness's own 2000px ceiling. On a 34-page CityU deck that is 3.3 MB on disk and 4.4 MB of base64 instead of 21.8 MB and 29.1 MB — an 85% cut with identical pixel dimensions, so nothing about what the model sees changes.

**Render with this script and nothing else.** Not `pdftoppm`, not `pdftocairo`, not `qlmanage`, not `sips`, not a Python PDF library. A hand-rolled `pdftoppm -png` produces exactly the PNG pages this step exists to avoid, so bypassing the script restores the 29 MB request that gets the deck rejected. The script is not a convenience wrapper: the DPI ceiling, the edge ceiling, the WebP encode, the verification of every delivered page, and the removal of each intermediate PNG all live inside it.

**If the script fails, stop and report it.** A missing `cwebp` or `pdftoppm`, a corrupt page, an unverified output: say which page and why, and do not substitute another route. `preflight.py` already fails intake when either tool is absent, so a failure here is a real fault to surface, not an obstacle to route around.

Two rules inside the script make the ceiling hold, and both are the script's job rather than yours:

- **Never exceed the ceiling.** The harness passes a small image through untouched but re-encodes anything over 2000px, trying PNG first. A 2000×2827 WebP comes back out as a 1.9 MB PNG — worse than sending the original. `--max-edge` defaults to 2000 and refuses a larger value.
- **Never upscale.** `--dpi` is a ceiling, not a target: the script lowers it until the longer side fits. Ask for more resolution by raising `--dpi` only up to that limit.

The rendered pages then govern how you read them: batch size, the 200-image conversation ceiling, and what to do about a deck larger than that are in [3b](#3b-read-the-rendered-pages-natively).

### 3b. Read the rendered pages natively

The rendered pages are the only way in. Do not open the source PDF to read it: `read` refuses a PDF with a binary-file error, and a text layer cannot tell a section divider from a substantive page, which is the one judgement this whole pass exists to make. An image source is already an image and needs no rendering.

Read the pages, page by page, before planning. On each page decide: substantive content, structural skeleton (agenda, divider, outline), furniture (title bar, logo, page number, footer), or administrative (welcome, staff, schedule, exercises).

Record what you saw; do not rely on a text layer to tell you what a page was for. Read in batches of about eight pages and write each batch's verdict into the staging triage file before starting the next batch. Page images stay in the conversation for the rest of the session, and the provider accepts at most 200 of them, so the batching is what keeps a long deck inside a conversation that also has to hold the note, the Canvas, and the QA state. A document with more pages than the conversation can hold is the case for `--extraction mineru`, not for reading faster.

## 3c. Optional MinerU extraction

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

Extract only visuals whose structure matters and name them per [asset-naming.md](asset-naming.md). Record one `evidence` phrase per kept page in the ledger. Crop to the figure, not to the slide.

## 5b. Bounding the delivered assets

Run `scripts/optimize-assets.py`:

```text
scripts/optimize-assets.py <document-folder> --vault-root <vault-root> \
  --ledger <run>/page-ledger.json --report <run>/asset-optimization.json
```

Extraction hands over full-resolution page renders: the MinerU adapter copies its downloads byte for byte, and native reading saves whatever the page looked like. A reader sees an embed at a few hundred pixels, so those bytes are never read. This step delivers every raster as WebP within a 1600px longest edge, rewrites the note embeds, the Canvas file nodes, and the ledger, and unlinks an original only after a vault-wide scan proves nothing references it. Add `--dry-run` to see the byte totals before touching a folder that already exists.

Run it before the Canvas is delegated. The Canvas then points at delivered file names, and the render-QA hash it measures stays the hash of the file on disk. An asset that would not shrink keeps its current file and is reported under `kept`; a `.gif` or `.svg` passes through untouched.

### Optional deterministic LaTeX normalization

Disabled by default. When enabled, load `obsidian-latex-refiner` and run `scripts/normalize-latex.py --target <note> --vault-root <root> --snapshot <run>/before.md --report <run>/latex-refinement-report.json`. It rewrites only math syntax, keeps visible text and links intact, treats a marker-free note as one segment, and restores the snapshot on any conservation failure. Delete the snapshot and report after success.

## 6. Derived artifacts

Write:

- the note or notes;
- a flat `assets/` directory of delivered WebP files referenced from the notes;
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
