# Bundled scripts

This directory contains only state cleanup in phase one; it remains empty of conversion code.

- `purge-state.sh --confirm` removes the registry and its in-skill backups before uninstall. It does not touch course files or any path outside `state/`.

Future scripts belong here only when they provide deterministic, reusable behavior such as:

- inspecting PDF page characteristics;
- invoking a supported extraction backend;
- normalizing extracted assets and links;
- validating the output contract;
- producing a machine-readable conversion report.

Each executable must document inputs, outputs, exit codes, dependencies, offline/network behavior, and overwrite rules. It must have tests before `SKILL.md` instructs an agent to run it.
