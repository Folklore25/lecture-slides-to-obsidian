# Bundled scripts

This directory is intentionally empty of conversion code in phase one.

Future scripts belong here only when they provide deterministic, reusable behavior such as:

- inspecting PDF page characteristics;
- invoking a supported extraction backend;
- normalizing extracted assets and links;
- validating the output contract;
- producing a machine-readable conversion report.

Each executable must document inputs, outputs, exit codes, dependencies, offline/network behavior, and overwrite rules. It must have tests before `SKILL.md` instructs an agent to run it.
