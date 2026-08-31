# Conversion report

## Matched routing

| Field | Value |
| --- | --- |
| Semester ID | {{semester_id}} |
| Semester label | {{semester_label}} |
| Course key | {{course_key}} |
| Course folder | {{course_folder}} |
| Document folder | {{document_folder}} |
| Routing candidates shown | {{routing_candidates}} |
| Routing decision | {{routing_decision}} |

## Pipeline

| Field | Value |
| --- | --- |
| Provider | MinerU Precision API v4 |
| Model | {{mineru_model}} |
| Conversion profile | {{conversion_profile}} |
| Language | {{language}} |
| OCR | {{is_ocr}} |
| Formula recognition | {{enable_formula}} |
| Table recognition | {{enable_table}} |
| Source filename | {{source_filename}} |
| Source SHA-256 | {{source_sha256}} |
| Source pages | {{source_pages}} |
| Redacted batch reference | {{batch_reference}} |

## Outputs

| Artifact | Relative path | Status |
| --- | --- | --- |
| Complete Markdown | {{markdown_path}} | {{markdown_status}} |
| Relationship canvas | {{canvas_path}} | {{canvas_status}} |
| Assets directory | {{assets_path}} | {{assets_status}} |
| Conversion report | conversion-report.md | created |

## Content inventory

| Type | Count | Notes |
| --- | ---: | --- |
| Pages | {{page_count}} | |
| Figures/images | {{figure_count}} | |
| Tables | {{table_count}} | |
| Equations | {{equation_count}} | |
| Fallback pages | {{fallback_page_count}} | |
| Page headers | {{page_header_count}} | {{page_header_notes}} |
| Page footers | {{page_footer_count}} | {{page_footer_notes}} |
| Page footnotes | {{page_footnote_count}} | {{page_footnote_notes}} |

## Quality gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Source original excluded from vault | {{source_exclusion_status}} | {{source_exclusion_evidence}} |
| Page/block structural alignment | {{structural_status}} | content list + layout metadata |
| Page markers valid | {{page_marker_status}} | {{page_marker_evidence}} |
| Obsidian Markdown validation | {{markdown_validation_status}} | {{markdown_validation_evidence}} |
| Canvas validation | {{canvas_validation_status}} | {{canvas_validation_evidence}} |
| Asset links resolve | {{asset_link_status}} | {{asset_link_evidence}} |
| Secret-safety scan | {{secret_scan_status}} | {{secret_scan_evidence}} |

## Review items

- {{review_item}}

## Not checked

- Pixel-level visual diff against rendered source pages: NOT-CHECKED — {{pixel_visual_diff_reason}}
- {{not_checked_item}}
