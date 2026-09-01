# Live classroom workflow

## Note binding

The user normally has the course note and terminal open together. The terminal can be the active leaf, so discover Markdown leaves with `obsidian eval`, not `obsidian file` alone. Prefer an already open note whose frontmatter has `type: course-material` and `conversion_profile: lecture-notes`.

Bind once per chat. Re-resolve only when the user explicitly changes course/note or the bound path disappears.

## Fast routing

For each thought:

1. obtain the outline with `obsidian outline path=<path> format=json`;
2. read only plausible sections when possible;
3. route to the narrowest exact H2/H3 with strong semantic overlap;
4. otherwise append under `## In-class notes` as unresolved.

Do not ask the learner to choose among headings for every thought. A short unresolved inbox is preferable to disrupting the lecture.

## Response style

Successful response:

```text
已补充到「Business model fit」：你的想法已作为 In-class connection 保存。
```

Unresolved response:

```text
暂存到「In-class notes」；课后可以再归位。
```

Do not repeat the full thought unless needed to confirm a risky interpretation.
