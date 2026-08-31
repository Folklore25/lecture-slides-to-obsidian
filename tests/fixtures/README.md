# Fixture policy

Test fixtures are divided by redistribution status:

```text
fixtures/
├── synthetic/   # generated in-house and safe to commit
├── public/      # openly licensed, with source and license metadata
├── private/     # local-only real course material; ignored by Git
└── inbox/       # temporary local intake; ignored by Git
```

## Synthetic fixtures

Prefer small PDFs designed to isolate one behavior: reading order, equations, tables, diagrams, OCR, mixed Chinese/English, or rotated pages. Store the generator source beside the PDF so the fixture is reproducible.

## Public fixtures

Every public fixture must include a metadata file with source URL, author, license, retrieval date, and any modifications. Do not rely on “available online” as permission to redistribute.

## Private fixtures

Real Canvas course files belong only in `private/` or outside the repository. Never commit them, derived page images, extracted text, student names, Canvas cookies, access tokens, or signed download URLs. Private fixtures may be used for local manual evaluation, but results must be summarized without exposing course content.

## Fixture manifest

Each committed fixture should be registered in a case manifest with the expected capability class and the behaviors under test. Do not encode a backend-specific output format in the manifest.
