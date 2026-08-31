# Skill-owned runtime state

The installed skill creates `course-registry.yaml` in this directory. The file contains local semester roots and course mappings and is intentionally ignored by Git.

Keep all registry backups in this directory so deleting the skill removes its state. Do not store credentials, Canvas sessions, or course content here.

An updater that replaces the whole skill directory must preserve this directory and restore it in place. Package updates must never replace a real registry with the example file.

Use `course-registry.example.yaml` as the schema example. To remove local routing state before uninstall or before a manager creates a backup, run:

```bash
../scripts/purge-state.sh --confirm
```
