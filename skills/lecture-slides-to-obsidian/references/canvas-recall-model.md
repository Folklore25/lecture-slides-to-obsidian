# Recall-model schema

Write this JSON under staging after reading the complete Markdown. It is the semantic input to `build-canvas.py`, not a vault artifact.

## Top-level fields

```json
{
  "schema_version": 1,
  "profile": "lecture-notes",
  "mode": "pre-class",
  "title": "Document title",
  "orientation": {},
  "groups": [],
  "concepts": [],
  "relations": [],
  "coverage": [],
  "synthesis": {},
  "asset_links": []
}
```

`profile` is `lecture-notes`, `policy-document`, or `paper`. `mode` is `pre-class` or `post-class`.

## Orientation

```json
{
  "central_question": "What problem does this material help the learner solve?",
  "one_sentence_answer": "A direct answer that states the governing idea and outcome.",
  "takeaways": ["Three to five durable, source-supported takeaways."]
}
```

Do not use an administrative title such as “Week 4 slides” as the central question.

## Groups

Two to seven learning modules, ordered by the logic needed to understand the subject:

```json
{"id":"foundations","title":"Foundations","summary":"The ideas needed before the mechanism makes sense.","order":1}
```

Group by meaning. Do not mechanically create one group per slide or one group per Markdown heading.

## Concepts

Four to twenty atomic recall nodes; eight to sixteen is the normal target for a full lecture:

```json
{
  "id": "control-signal",
  "group": "foundations",
  "kind": "concept",
  "title": "Control signal",
  "statement": "A concise statement of one idea and why it matters.",
  "details": ["Up to three details needed to reconstruct the idea."],
  "recall_cue": "A short question or contrast that triggers retrieval.",
  "source_heading": "Exact H2 heading from the Markdown",
  "source_page": 4
}
```

Allowed `kind` values:

`foundation`, `concept`, `mechanism`, `process`, `evidence`, `example`, `application`, `comparison`, `boundary`, `misconception`, `decision`, `claim`, `method`, `finding`, `limitation`, `rule`, `exception`.

Use at least three kinds. A title plus copied paragraph is not an atomic recall node. `source_page` is required even when the heading is unique; the heading/page pair must occur in the Markdown, preserving exact provenance when headings repeat. Within each group, list concepts in the visual/logical order the renderer should preserve.

## Relations

```json
{
  "from": "control-signal",
  "to": "system-response",
  "type": "causes",
  "label": "changes the system state",
  "why": "The source describes the response as the effect of the applied control signal."
}
```

`why` is staging evidence and is not rendered. Allowed `type` values are listed in [canvas-contract.md](canvas-contract.md). The undirected form of the concept graph must be connected.

## Coverage ledger

Include one entry for every exact H2 heading in the Markdown:

```json
{"source_heading":"System behavior","source_page":4,"concepts":["control-signal","system-response"]}
```

If a section is non-substantive or empty, keep the row and explain:

```json
{"source_heading":"In-class notes","source_page":12,"concepts":[],"omission_reason":"Empty in pre-class mode."}
```

Never omit a section from the ledger because it is difficult to summarize. Coverage identity is the exact `(source_heading, source_page)` pair, so repeated headings on different pages remain separate.

## Synthesis

```json
{
  "logic_chain": ["Three to seven steps that reconstruct the lesson."],
  "distinctions": [
    {"terms":"Positive vs negative feedback","rule":"State the decision rule that separates them."}
  ],
  "recall_prompts": ["Three to five questions answerable from the map."],
  "in_class_additions": []
}
```

The logic chain is the shortest coherent reconstruction of the lesson, not a list of section names. `in_class_additions` must be empty before class and may contain only confirmed notes after class.

## Asset links

Select zero to six visuals whose structure materially aids recall:

```json
{
  "concept": "system-response",
  "path": "assets/page-006-chart-01.png",
  "caption": "Response curve showing overshoot and settling"
}
```

Do not include decorative images, logos, repeated headers, or every extracted figure.
