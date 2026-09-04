# Enrichment-plan schema

```json
{
  "schema_version": 1,
  "note": "COURSE101/Lectures/example/example.md",
  "asr_source": "teacher-session.md",
  "entries": [
    {
      "id": "teacher-20260901-001",
      "actor": "teacher",
      "kind": "example",
      "target_heading": "Core concept",
      "target_level": 2,
      "body": "The lecturer used a queue at a busy café to illustrate the bottleneck.",
      "source_anchor": "00:31:24",
      "evidence": "short ASR evidence fragment",
      "novelty_basis": "new-example",
      "confidence": "high",
      "apply": true,
      "routing_status": "matched"
    }
  ],
  "no_additions_reason": null
}
```

Allowed `novelty_basis` values:

`new-explanation`, `new-example`, `new-emphasis`, `correction`, `boundary-condition`, `question-answer`, `new-logistics`.

Each applied entry must use actor `teacher`, an allowed teacher kind, exact target H2/H3, evidence, source anchor, novelty basis, and high/medium confidence. Only the source anchor and confidence reach the inserted callout; evidence and novelty basis are staging/review metadata and never appear in the note. Entries with `apply: false` remain staging review items and are omitted from the insertion patch.

An empty `entries` array is valid only with a concrete `no_additions_reason`.
