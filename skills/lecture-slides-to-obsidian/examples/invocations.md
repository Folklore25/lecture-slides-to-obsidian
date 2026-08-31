# Synthetic invocation examples

These examples show intent and expected questions. Paths and course names are fictional.

## Standard preparation

```text
Convert ./downloads/IS0000-Lecture03.pdf for IS0000 into an Obsidian-ready pre-class note. Keep diagrams as visual fallbacks and do not overwrite an existing note.
```

On the first use in an unregistered semester, the agent asks for the semester root. After that semester becomes active, future courses and requests route beneath the registered root without asking for the path again.

## First course binding

```text
User: Prepare ./downloads/week-01.pdf for IS0000.
Agent: 这个学期的根目录在哪儿？
User: /path/to/vault/2026-fall
```

The agent then discovers or creates the `IS0000` course folder, records the mapping, and classifies the PDF, note, assets, and report under that course.

## Reused course binding

```text
Prepare ./downloads/week-02.pdf for Example Course.
```

If `Example Course` is a registered alias with one exact match in the active semester, the agent reuses the stored destinations without another directory question.

## New course in the active semester

```text
Prepare ./downloads/week-01.pdf for CS0001.
```

If `CS0001` is not registered but the active semester root is valid, the agent discovers or creates its course folder under that root and records it without asking for the semester path again.

## Explicit review policy

```text
Prepare Lecture 06 from ./slides/week-06.pdf. Use English and Chinese language hints, keep page provenance, and flag every equation you cannot verify from the source.
```

## Backend not chosen

```text
Inspect this lecture PDF and recommend whether it needs the fast, layout-aware, or OCR path. Do not run a network service or install a large model yet.
```
