#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
skill_dir="$repo_dir/skills/lecture-slides-to-obsidian"

required_files='SKILL.md
agents/openai.yaml
config/README.md
config/pipeline.example.yaml
examples/invocations.md
examples/expected-note.md
requirements/skills.yaml
requirements/services.yaml
references/workflow.md
references/course-routing.md
references/requirements.md
references/mineru-api.md
references/output-contract.md
references/obsidian-style.md
references/quality-gates.md
scripts/README.md
scripts/purge-state.sh
state/README.md
state/course-registry.example.yaml'

printf '%s\n' "$required_files" | while IFS= read -r relative_path; do
  if [ ! -f "$skill_dir/$relative_path" ]; then
    printf 'missing: %s\n' "$relative_path" >&2
    exit 1
  fi
done

if ! grep -q '^name: lecture-slides-to-obsidian$' "$skill_dir/SKILL.md"; then
  printf 'invalid or missing skill name\n' >&2
  exit 1
fi

if ! grep -q '^description: .\+' "$skill_dir/SKILL.md"; then
  printf 'missing skill description\n' >&2
  exit 1
fi

if grep -R -n -E '\[TODO|TODO:|FIXME' "$repo_dir" \
  --exclude-dir=.git \
  --exclude=validate.sh >/dev/null 2>&1; then
  printf 'unfinished placeholder found\n' >&2
  exit 1
fi

if find "$repo_dir/tests/fixtures/private" -type f ! -name README.md -print 2>/dev/null | grep -q .; then
  printf 'private fixture found; keep it outside version control\n' >&2
  exit 1
fi

if grep -R -n '/Users/\|/home/' "$skill_dir/config" "$repo_dir/tests/cases" >/dev/null 2>&1; then
  printf 'machine-specific path found in committed examples\n' >&2
  exit 1
fi

if grep -R -n '~/.config/lecture-slides-to-obsidian\|XDG_CONFIG_HOME' "$skill_dir" \
  --exclude=README.md >/dev/null 2>&1; then
  printf 'external registry path found; runtime state must stay inside the skill\n' >&2
  exit 1
fi

if ! grep -q 'required-skills: "obsidian-markdown"' "$skill_dir/SKILL.md"; then
  printf 'skill prerequisite metadata is missing or out of sync\n' >&2
  exit 1
fi

if ! grep -q 'required-services: "MinerU Precision API v4"' "$skill_dir/SKILL.md"; then
  printf 'service prerequisite metadata is missing or out of sync\n' >&2
  exit 1
fi

if grep -q 'mineru-pdf\|runtime_command' "$skill_dir/requirements/skills.yaml"; then
  printf 'local MinerU skill/runtime dependency is forbidden\n' >&2
  exit 1
fi

if ! grep -q 'POST /api/v4/file-urls/batch' "$skill_dir/requirements/services.yaml" || \
   ! grep -q 'GET /api/v4/extract-results/batch/{batch_id}' "$skill_dir/requirements/services.yaml"; then
  printf 'MinerU API endpoint contract is missing or out of sync\n' >&2
  exit 1
fi

printf 'repository skeleton: ok\n'
