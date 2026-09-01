# Persistent course routing

Use the skill-owned registry so semester and course destinations survive across sessions. Source originals remain at their external input locations; the registry routes only derived Obsidian artifacts.

## Registry

Resolve the directory containing this skill's `SKILL.md`, then use:

```text
<skill-directory>/state/course-registry.yaml
```

Use [../state/course-registry.example.yaml](../state/course-registry.example.yaml) as the schema. Write atomically inside `state/`; keep migration backups there. The registry never stores credentials, Canvas sessions, course content, or plaintext API tokens; encrypted token state is owned separately by `token-store.py`.

## Semester identity is independent from the path

Each semester record has an explicit `id`, `label`, and absolute `vault_root`. Do not assume the root folder name is the semester ID.

When registering a semester:

1. Ask for the destination root inside the Obsidian vault.
2. If the path contains an unambiguous semester token such as a year plus `fall`, `spring`, `semester-1`, or `semester-2`, propose a normalized ID and let the user correct it.
3. If the path is generic, such as `Courses`, ask once for the semester label/ID. Store the generic path unchanged and the semester identity separately.
4. Do not fabricate a semester ID from a school, vault, or generic folder name.

The normal case needs one root response. A second semester-ID question is required only when the path does not carry reliable semester information.

## Course matching

Normalize strings with Unicode compatibility normalization, case folding, collapsed whitespace, and equivalent spaces/hyphens in course codes. Keep original values as aliases.

Automatic routing requires a unique exact match in this order:

1. course key or normalized course code in the active semester;
2. registered exact alias or full course name in the active semester;
3. a unique exact match across all semesters only when no valid active semester exists.

If no exact match exists, inspect immediate course directories and list plausible candidates before creating anything. For example, `<course>-materials` may be related to the requested course without being its canonical folder. Show candidates and ask whether to reuse one or create the canonical folder. Never auto-route or silently dismiss a fuzzy candidate.

Record the candidate list and the user's decision in the temporary QA context. If no plausible candidate exists, create a safe course folder from the course code, otherwise a sanitized course name.

## Derived output layout

Every source document gets one self-contained derived folder:

```text
<vault_root>/
└── <course-folder>/
    └── Lectures/
        └── <document-slug>/
            ├── <document-slug>.md
            ├── <document-slug>.canvas
            └── assets/
```

Registered role paths may differ, but the document folder must contain only the complete Markdown, extracted assets, and knowledge-recall Canvas. Temporary reports and recall models remain under system tmp or the installed skill directory, outside the vault.

## Source originals stay external

- Never copy, move, symlink, embed, or create a Canvas file node for the original PDF/PPT/PPTX/DOC/DOCX/XLS/XLSX/archive.
- Read and upload the source from its existing external path.
- The final note may record source basename, format, size, page count, and SHA-256, but not an absolute source path unless the user explicitly requests it.
- Optional `source_materials_root` belongs in the skill-owned registry and must resolve outside the registered `vault_root`.

## Path safety

- Store `vault_root` and optional `source_materials_root` as absolute paths; store all derived child destinations as relative paths.
- Reject empty child paths, absolute child paths, path separators in generated keys, and any `..` segment.
- Resolve symlinks and verify every derived destination remains under the course folder.
- Reject any source path that resolves inside `vault_root` unless the user first moves it outside the vault.
- Never fall back to the working directory when a registered destination is invalid.

## Registry maintenance

Keep at most one active semester unless concurrent semesters are explicitly needed. When a path moves, update the existing record rather than creating a duplicate. Before a manager creates an uninstall backup, run `scripts/purge-state.sh --confirm` if local paths must not remain in that backup.
