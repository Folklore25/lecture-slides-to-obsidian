# Layered note insertion contract

All classroom additions are separate callout blocks with stable HTML-comment markers. The original course-material transcription remains untouched.

## Patch schema

```json
{
  "schema_version": 1,
  "note": "COURSE101/Lectures/example/example.md",
  "entries": [
    {
      "id": "student-20260901T143022-001",
      "actor": "student",
      "kind": "connection",
      "target_heading": "Core concept",
      "target_level": 2,
      "body": "This connects to the earlier distinction between incentives and constraints.",
      "captured_at": "2026-09-01T14:30:22+08:00",
      "routing_status": "matched"
    }
  ]
}
```

`note` is an exact vault-relative Markdown path. `target_heading` must match exactly one H2 or H3 of `target_level` 2 or 3.

The target note must have frontmatter `type: course-material`; the apply tool rejects ordinary notes to prevent accidental insertion into the wrong open tab.

## Student kinds

`thought`, `connection`, `question`, `interpretation`, `example`, `disagreement`, `hypothesis`, `action`.

## Teacher kinds

`explanation`, `example`, `emphasis`, `correction`, `boundary`, `question-answer`, `logistics`.

## Rendered blocks

Student example:

```markdown
<!-- lecture-layer:student:student-20260901T143022-001:start -->
> [!note] In-class connection
> This connects to the earlier distinction between incentives and constraints.
>
> _Captured: 2026-09-01T14:30:22+08:00_
<!-- lecture-layer:student:student-20260901T143022-001:end -->
```

Teacher additions use appropriate built-in callouts such as `example`, `important`, `warning`, `info`, or `question`, and include an ASR source anchor when supplied.

## Placement and safety

- Insert at the end of the selected section, immediately before the next heading whose level is equal or higher.
- Preserve insertion order within a section.
- If the entry marker already exists, report `already_present` and do not duplicate it.
- Reject marker syntax inside body text, duplicate patch IDs, ambiguous headings, missing `## In-class notes` fallback, absolute paths, `..`, and non-Markdown targets.
- The mutation may add only complete lecture-layer blocks plus separator newlines. Every pre-existing source line must remain byte-for-byte and in the same order.

The apply tool has two backends. The live-notes workflow uses `--backend obsidian-cli`: normal-size notes are written with `obsidian create ... overwrite`; notes too large for a safe process argument use an atomic filesystem replacement followed by mandatory Obsidian CLI readback and SHA verification. The post-class ASR enricher uses `--backend fs`, which reads and writes the vault file directly (atomic replace plus SHA readback) without the Obsidian CLI.
