# Persistent course routing

Use a local registry so the user supplies a semester root once per semester and later conversions can route by course name alone.

## Registry location and ownership

Resolve the directory containing this skill's `SKILL.md`, then use:

```text
<skill-directory>/state/course-registry.yaml
```

The real registry is skill-owned local state. Do not redirect it to a user-level config directory, an Obsidian note, or this Git repository. It may contain private absolute paths, but never credentials or Canvas session data. Removing the installed skill directory removes this state with it.

Use [../state/course-registry.example.yaml](../state/course-registry.example.yaml) as the schema example. Preserve unknown fields when updating a compatible schema. Write changes atomically inside `state/` and keep a recoverable previous copy there before a schema migration. Do not place registry backups outside the skill directory.

## First encounter

When the user supplies a course name or course code:

1. Normalize it for matching without replacing the original display value.
2. Read the registry before asking for a destination.
3. If the course has one exact match in the valid active semester, reuse it without asking for a path.
4. If the course is new but a valid active semester exists, bind it under that semester root without asking for the root again.
5. If there is no valid active semester, ask: “这个学期的根目录在哪儿？” Validate the response and create a semester record. Derive a stable semester ID and display label from the root folder name without requiring another answer.
6. Inspect the semester root's immediate course directories. Prefer an exact normalized course-code or exact name match.
7. If one course directory matches, register it. If none matches, create a safe course folder from the course code when present, otherwise from a sanitized course name.
8. Detect existing classification subfolders by exact known role names. When no subfolders exist, create the default layout below.
9. Persist the semester, course aliases, relative course folder, and relative role destinations before conversion.

The normal first-use flow needs only the semester root response once per semester. Ask another question only when multiple plausible semester/course records, course folders, or subfolder-role candidates would make automatic classification unsafe.

## Default layout

```text
<semester-root>/
└── <course-folder>/
    ├── Slides/
    └── Lectures/
        ├── <lecture-slug>.md
        ├── assets/<lecture-slug>/
        └── reports/<lecture-slug>.conversion-report.md
```

- Copy the source PDF into `Slides/`; never move or delete the original.
- Place the Markdown note in `Lectures/`.
- Place extracted and fallback images in `Lectures/assets/<lecture-slug>/`.
- Place the conversion report in `Lectures/reports/`.
- If the user already has equivalent folders, register and reuse those relative paths instead of creating duplicates.

Recognize only exact role names during discovery. Suggested aliases are `Slides`, `Lecture Slides`, or `课件` for source slides, and `Lectures`, `Lecture Notes`, or `课堂笔记` for notes. If more than one existing folder fits a role, ask instead of choosing by similarity.

## Matching rules

Normalize candidate strings with Unicode compatibility normalization, case folding, trimmed/collapsed whitespace, and equivalent spacing/hyphen treatment in course codes. Keep every original alias for display and audit.

Automatic routing requires a unique exact match in this order:

1. course key or normalized course code in the active semester;
2. registered exact alias or full course name in the active semester;
3. a unique exact match across all registered semesters only when no valid active semester is configured.

Do not auto-route a fuzzy match. Fuzzy similarity may be shown as a suggestion, but the user must confirm it. If the same course exists in more than one semester, prefer the explicitly active semester; otherwise ask which semester applies. A course that is new to a valid active semester is registered there without asking for the semester root again.

## Path safety

- Store the semester root as an absolute path and every child destination as a relative path.
- Reject empty child paths, absolute child paths, path separators in generated course keys, and any `..` segment.
- Resolve symlinks and verify the course folder remains under the semester root and every destination remains under the course folder.
- If the registered root is missing or moved, ask for its new location once and update the existing semester record instead of creating a duplicate.
- Never fall back to the current working directory when a registered destination cannot be validated.

## Source-file collisions

If the target `Slides/` already contains the same filename:

- reuse it when content hashes match;
- when hashes differ, keep both with a deterministic disambiguated name and report the collision;
- never overwrite a different PDF silently.

## Registry maintenance

Add an alias only after a unique course has been resolved. Keep at most one active semester unless the user explicitly needs concurrent semesters. When a course folder or semester root changes, update the existing record and validate all derived destinations.

Before uninstalling through a manager that creates skill backups, run `scripts/purge-state.sh --confirm` if the backup must not retain local course paths.
