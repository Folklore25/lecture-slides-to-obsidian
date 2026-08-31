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

The agent records the mapping and creates a derived document folder for Markdown, assets, and Canvas. The PDF remains at `./downloads/week-01.pdf`; temporary QA remains in staging outside the vault.

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

## First encrypted-token setup

If encrypted state is absent, the agent discloses the upload and configures it:

```text
Agent: 这份课件将上传到 MinerU 官方 API。请提供 API token；我会立即加密保存到当前技能的 state 目录，不会回显或保存明文。
User: <plaintext MinerU API token>
```

The agent sends the token to `token-store.py set --token-stdin` through stdin, never a command argument. The script asks for a hidden encryption passphrase and writes `state/mineru-api-token.enc.json`.

## Reusing encrypted credentials

For later conversions, the agent does not ask for the API token again. It asks for the encryption passphrase through a hidden prompt, decrypts the token in process memory, and never prints it.

## Explicit review policy

```text
Prepare Lecture 06 from ./slides/week-06.pdf. Use English and Chinese language hints, keep page provenance, and flag every equation you cannot verify from the source.
```

The agent also asks whether OCR should be enabled for this document; it does not assume false.

## Non-slide course document

```text
Convert ./downloads/research-code-of-conduct.pdf for IS0000.
```

If structured MinerU output shows continuous policy prose rather than slides, the agent pauses before vault delivery and asks to confirm `policy-document`. It preserves numbered policy headings and does not add `## In-class notes` by default.

## Near-match course directory

```text
User: Convert week-01.pdf for IS6000.
Agent: 我没有找到 IS6000 的精确目录，但发现 Information_systems/。请确认是复用该目录，还是新建 IS6000/？
```

The decision is recorded in the conversion report.

## Backend not chosen

```text
Inspect the known metadata for this lecture PDF and recommend MinerU API options such as language, OCR, formula, table, and page range. Do not parse the PDF locally or request the API token yet.
```
