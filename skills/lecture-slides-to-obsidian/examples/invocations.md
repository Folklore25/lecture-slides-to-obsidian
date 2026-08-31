# Standardized invocation examples

All names and paths below are placeholders. Replace them with discovered user context; do not treat them as defaults.

## First use

```text
User: Convert /external/materials/example-lecture.pdf for COURSE101.
Agent: Which folder inside your Obsidian vault should contain this term's course folders?
User: /path/to/vault/example-term
```

The Agent confirms the course folder, profile, language, OCR choice, and encrypted token state in stages. The source remains outside the vault.

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

Profile is confirmed before upload. Structured MinerU output acts as a later mismatch check.

## Encrypted token setup

If encrypted state is absent, the Agent discloses the upload and configures it:

```text
Agent: This source will be uploaded to the official MinerU API. Provide the API token; I will encrypt it in this installed skill's state directory and will not echo or store plaintext.
User: <MinerU API token>
```

The Agent passes the token to `token-store.py set --token-stdin` through stdin, never a command argument. The script automatically stores a random wrapping key in macOS Keychain. Later conversions unlock automatically without asking again.

## API option confirmation

```text
Agent: Confirm MinerU language `en` and OCR `false` for this document.
```

Both fields require explicit values; neither uses a silent request default.
