# Quality gates

A conversion is complete only when the applicable gates pass or the report names the unresolved failure.

## Required checks

- The course resolved to one registered semester/course record without fuzzy or ambiguous matching.
- The resolved course and destination paths remain under the registered semester root.
- The source PDF copy, note, assets, and report use their registered role directories.
- The source PDF remains unchanged.
- The PDF was uploaded only through the MinerU Precision API v4 signed-upload flow.
- No local PDF parser, local MinerU runtime, lightweight API, or third-party wrapper was used.
- The Bearer token was sent only to `https://mineru.net`; signed upload/result downloads received no Bearer header.
- No API token, Authorization header, signed URL, or raw secret-bearing response exists in state, staging, output, reports, logs, or Git.
- ZIP members passed traversal, symlink, type, count, and extracted-size safety checks.
- The final Markdown file opens as UTF-8 and contains no unresolved temporary paths.
- All relative image links resolve inside the destination.
- Page provenance is monotonic and references valid source pages.
- Opening, middle, ending, and all flagged pages were visually compared with the source.
- Headings and lists follow the intended reading order.
- Equations and tables are either validated, preserved visually, or explicitly flagged.
- Complex diagrams retain a nearby visual fallback.
- Existing user-authored notes were not overwritten.
- The conversion report identifies MinerU Precision API v4, model/options, warnings, fallback pages, and checks performed without secret URLs.

## Useful metrics

Record page count, text-bearing pages, OCR pages, fallback pages, extracted assets, broken links, and manual-review pages. Metrics support maintenance decisions; they are not substitutes for visual inspection.

## Completion language

Say “converted with the listed fallbacks and review items,” not “lossless” or “perfect.” If visual comparison was sampled rather than exhaustive, state the sample and do not imply every page was checked.
