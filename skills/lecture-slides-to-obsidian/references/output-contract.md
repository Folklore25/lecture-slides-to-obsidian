# Output contract

The default deliverable is a portable set of artifacts classified under the registered semester and course:

```text
<semester-root>/
└── <course-folder>/
    ├── Slides/<source-pdf>
    └── Lectures/
        ├── <lecture-slug>.md
        ├── assets/<lecture-slug>/
        │   ├── page-003-figure-01.png
        │   └── page-007-fallback.png
        └── reports/<lecture-slug>.conversion-report.md
```

Registered destination names may differ, but their roles and containment rules remain the same. The final note must not depend on files left in a temporary directory.

## Lecture note

The Markdown note should contain:

1. YAML properties with known source metadata only.
2. A title and optional short navigation section.
3. Content in source order, divided into useful lecture sections.
4. Page provenance at a stable granularity.
5. Relative image or embed links.
6. Visible uncertainty markers only where review is actually needed.

Recommended provenance marker:

```markdown
<!-- source-page: 7 -->
```

## Assets

- Use deterministic, lowercase filenames.
- Keep the source page number in every extracted or fallback image filename.
- Prefer one asset per semantic figure when extraction is reliable.
- Prefer one full-page fallback image when relationships within the page cannot be represented safely.
- Do not duplicate identical assets without a reason.

## Conversion report

The report should state:

- matched semester, course key, and classified relative destinations;
- source filename and page count;
- backend and version, when known;
- conversion time and effective configuration;
- pages requiring OCR, fallback images, or manual review;
- counts of generated notes and assets;
- warnings, failures, and skipped content;
- validation performed and limitations not checked.

The report is diagnostic, not part of the lecture note's learning content.

## Overwrite and idempotence

Default to no overwrite. A repeated conversion with identical input and configuration should produce stable paths and avoid uncontrolled duplicate assets. User-authored additions in an existing Obsidian note must never be replaced by an automated rerun without an explicit merge strategy.
