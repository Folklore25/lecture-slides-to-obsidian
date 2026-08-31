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

## Official API token collection

After routing and file validation, the agent discloses the upload and requests the token:

```text
Agent: 这份课件将上传到 MinerU 官方 API。请在输入框粘贴本次使用的 API token。token 会以明文进入当前会话，可能由当前 Agent 宿主保留；我不会回显、写入文件、注册表、配置、日志或报告。
User: <plaintext MinerU API token>
```

The agent must not quote the user's second message. It uses the token only for MinerU API requests in the current conversion and discards it afterward.

## Explicit review policy

```text
Prepare Lecture 06 from ./slides/week-06.pdf. Use English and Chinese language hints, keep page provenance, and flag every equation you cannot verify from the source.
```

## Backend not chosen

```text
Inspect the known metadata for this lecture PDF and recommend MinerU API options such as language, OCR, formula, table, and page range. Do not parse the PDF locally or request the API token yet.
```
