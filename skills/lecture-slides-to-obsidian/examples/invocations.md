# Standardized invocation examples

All names and paths below are placeholders. Replace them with discovered user context; do not treat them as defaults.

## First use

```text
User: Convert /external/materials/example-lecture.pdf for COURSE101.
Agent: Which folder inside your Obsidian vault should contain this term's course folders?
User: /path/to/vault/example-term
```

The Agent confirms the course folder, the extraction mode, the note granularity, and the profile in stages. The source remains outside the vault.

## Extraction mode is chosen first

```text
Agent: I can read this deck directly and write the notes myself, which preserves the layout and the comparison tables.
       That needs a model that can see the pages, which this one can. Proceed natively, or should I run MinerU as an aid?
User: Read it yourself.
```

Native reading is the default. MinerU is only selected when the model cannot view the source, when the document is long or scanned, or when the user asks for it.

## Note granularity is always asked

```text
Agent: This deck has four numbered sections across 44 pages. Do you want one note with those sections as headings
       (single-note), or one note per section (section-notes)?
User: One note, sections as headings.
```

`preflight.py` emits this question on every `lecture-notes` conversion. There is no default.

## Existing course mapping

```text
Convert /external/materials/example-lecture-02.pdf for COURSE101.
```

When `COURSE101` has one exact match in the active term, the stored destination is reused without another path question.

## Near-match folder

```text
User: Convert example-lecture.pdf for COURSE101.
Agent: I did not find an exact COURSE101 folder, but found course-101-materials. Should I reuse it or create COURSE101?
```

The Agent records the decision in temporary QA context.

## Profile suggestion

```text
User: Convert /external/materials/example-policy.pdf for COURSE101.
Agent: The filename suggests policy-document rather than lecture-notes. Use policy-document?
```

Profile is confirmed before any writing.

## MinerU as an optional aid

```text
User: This one is a 180-page scan; use MinerU this time.
Agent: This source will be uploaded to the official MinerU API. You already stored an encrypted token, so I will reuse it.
       Confirm language `en` and OCR `true` for this document.
```

Only with `--extraction mineru`. The Agent passes the token to `token-store.py set --token-stdin` through stdin when state is absent, never as a command argument, and reuses the encrypted token silently afterwards.

## Text-only model

```text
Agent: This model cannot view PDF pages, so native reading is not available. Re-running with --extraction mineru to keep the
       conversion faithful rather than guessing from a text layer alone.
```

Never run native conversion on a model that cannot see the source.

## Skeleton review

```text
Agent: plan-note-structure.py proposed five sections and marked nine pages as furniture. I read the deck and adjusted two
       headings; the plan and ledger are now final and every kept page carries an evidence phrase.
```
