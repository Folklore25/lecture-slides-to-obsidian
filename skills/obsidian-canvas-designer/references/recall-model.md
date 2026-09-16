# Recall model

The Canvas is built from an Agent-authored semantic model, never inferred from Markdown headings.

Start with `scripts/recall-skeleton.py --note <note> --profile <profile> --output <staging>/recall-model.json`. It inventories exact H2 anchors, H3 review candidates, page provenance when the note has it, and coverage rows. The output is an intentionally invalid authoring draft; fill its semantic fields before `build-canvas.py`.

## Page provenance is optional

- A note with `<!-- source-page: N -->` markers (MinerU transcription) gives every H2 a page anchor. There, `source_page` is required and the heading/page pair must occur in the note.
- A content-driven note has no page markers. There, omit `source_page` entirely and identify a section by its heading alone. The skeleton reports `page_provenance: "none"` so you can tell the two cases apart.

Never add page markers to a note to satisfy this skill, and never promote H3 headings. If a note has no usable H2 anchors, stop and return the H3 candidates for authorized repair.

## `concept.source_heading` is a hard contract

It must equal a real `## H2` heading in the Markdown. H1, H3, generated labels, and approximate text do not count.

```json
{
  "schema_version": 1,
  "profile": "lecture-notes",
  "mode": "pre-class",
  "title": "Week 3 Qualitative Research",
  "orientation": {
    "central_question": "...",
    "one_sentence_answer": "...",
    "takeaways": ["...", "...", "..."]
  },
  "groups": [
    {"id": "foundations", "title": "Foundations", "summary": "...", "order": 1}
  ],
  "concepts": [
    {
      "id": "technique",
      "group": "foundations",
      "kind": "boundary",
      "title": "Technique is not method",
      "statement": "...",
      "details": ["..."],
      "recall_cue": "...",
      "source_heading": "1. Research methodology and the qualitative distinction"
    }
  ],
  "relations": [],
  "coverage": [
    {"source_heading": "1. Research methodology and the qualitative distinction", "concepts": ["technique"]}
  ],
  "synthesis": {
    "logic_chain": [],
    "distinctions": [],
    "recall_prompts": [],
    "in_class_additions": []
  },
  "asset_links": []
}
```

Keep every concept card atomic and scannable: an H3 title, one short statement, at most two details, one recall cue, and one compact source link. Titles are limited to 60 Latin or 30 CJK characters, statements to 180 characters, and details to two items of 140 characters each.

## Coverage ledger

The model's `coverage` must include one entry for every H2 heading in the note.

- With page provenance: one entry per heading/page occurrence, so repeated headings stay distinct.
- Without page provenance: one entry per heading, and duplicate headings are an error the note must fix rather than something the Canvas can disambiguate.

Each entry either maps to concept ids or gives a concrete `omission_reason`. This is how the Canvas stays concise without pretending to contain the full note.

Delete the temporary model together with the conversion report after successful validation. Keep it only while debugging a failed build.
