#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
skill_dir="$repo_dir/skills/lecture-slides-to-obsidian"
canvas_skill_dir="$repo_dir/skills/obsidian-canvas-designer"
live_notes_skill_dir="$repo_dir/skills/obsidian-live-lecture-notes"
asr_skill_dir="$repo_dir/skills/lecture-asr-enricher"
layout_skill_dir="$repo_dir/skills/slide-layout-refiner"

main_required_files='SKILL.md
agents/openai.yaml
config/README.md
config/pipeline.example.yaml
examples/invocations.md
examples/expected-note.md
requirements/skills.yaml
requirements/services.yaml
requirements/tools.yaml
references/workflow.md
references/canvas-batch-delegation.md
references/course-routing.md
references/document-profiles.md
references/requirements.md
references/mineru-cli.md
references/mineru-normalization.md
references/normalization-examples.md
references/asset-naming.md
references/output-contract.md
references/obsidian-style.md
references/quality-gates.md
references/validation.md
scripts/README.md
scripts/plan-canvas-batch.py
scripts/fill-report.py
scripts/mineru-cli-adapter.py
scripts/preflight.py
scripts/reconstruct-note.py
scripts/purge-state.sh
scripts/token-store.py
scripts/validate-output.py
state/README.md
state/course-registry.example.yaml
templates/report-context.example.json
templates/canvas-batch-manifest.example.json'

canvas_required_files='SKILL.md
agents/openai.yaml
config/render-profile.mbp14-composer.json
references/axton-aesthetics.md
references/asset-contract.md
references/canvas-contract.md
references/delegation-contract.md
references/recall-model.md
references/render-qa.md
requirements/skills.yaml
requirements/tools.yaml
scripts/build-canvas.py
scripts/canvas-aesthetic-qa.py
scripts/canvas-render-qa.py
scripts/recall-skeleton.py
templates/delegated-task.md
templates/recall-model.lecture-notes.example.json'

live_notes_required_files='SKILL.md
agents/openai.yaml
references/insertion-contract.md
references/live-workflow.md
requirements/skills.yaml
requirements/tools.yaml
scripts/apply-note-patches.py
templates/live-note-patch.example.json'

asr_required_files='SKILL.md
agents/openai.yaml
references/enrichment-plan.md
references/novelty-policy.md
requirements/skills.yaml
requirements/tools.yaml
scripts/validate-enrichment-plan.py
templates/enrichment-plan.example.json'

layout_required_files='SKILL.md
agents/openai.yaml
references/refinement-contract.md
references/native-markdown-layout.md
requirements/skills.yaml
requirements/tools.yaml
scripts/validate-layout-refinement.py
templates/multimodal-layout-task.md'

printf '%s\n' "$main_required_files" | while IFS= read -r relative_path; do
  if [ ! -f "$skill_dir/$relative_path" ]; then
    printf 'main skill missing: %s\n' "$relative_path" >&2
    exit 1
  fi
done

printf '%s\n' "$canvas_required_files" | while IFS= read -r relative_path; do
  if [ ! -f "$canvas_skill_dir/$relative_path" ]; then
    printf 'Canvas skill missing: %s\n' "$relative_path" >&2
    exit 1
  fi
done

printf '%s\n' "$live_notes_required_files" | while IFS= read -r relative_path; do
  if [ ! -f "$live_notes_skill_dir/$relative_path" ]; then
    printf 'live-notes skill missing: %s\n' "$relative_path" >&2
    exit 1
  fi
done

printf '%s\n' "$asr_required_files" | while IFS= read -r relative_path; do
  if [ ! -f "$asr_skill_dir/$relative_path" ]; then
    printf 'ASR enricher skill missing: %s\n' "$relative_path" >&2
    exit 1
  fi
done

printf '%s\n' "$layout_required_files" | while IFS= read -r relative_path; do
  if [ ! -f "$layout_skill_dir/$relative_path" ]; then
    printf 'layout refiner skill missing: %s\n' "$relative_path" >&2
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

if ! grep -q '^name: obsidian-canvas-designer$' "$canvas_skill_dir/SKILL.md" || \
   ! grep -q '^description: .\+' "$canvas_skill_dir/SKILL.md"; then
  printf 'invalid Canvas subskill metadata\n' >&2
  exit 1
fi

if ! grep -q '^name: obsidian-live-lecture-notes$' "$live_notes_skill_dir/SKILL.md" || \
   ! grep -q '^description: .\+' "$live_notes_skill_dir/SKILL.md" || \
   ! grep -q '^name: lecture-asr-enricher$' "$asr_skill_dir/SKILL.md" || \
   ! grep -q '^description: .\+' "$asr_skill_dir/SKILL.md"; then
  printf 'invalid supplementary skill metadata\n' >&2
  exit 1
fi

if ! grep -q '^name: slide-layout-refiner$' "$layout_skill_dir/SKILL.md" || \
   ! grep -q '^description: .\+' "$layout_skill_dir/SKILL.md"; then
  printf 'invalid slide layout refiner metadata\n' >&2
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

if grep -R -n '/Users/\|/home/' "$skill_dir/config" "$canvas_skill_dir/config" "$repo_dir/tests/cases" >/dev/null 2>&1; then
  printf 'machine-specific path found in committed examples\n' >&2
  exit 1
fi

if grep -R -n -E 'Claude Code|Codex|Cursor|Coding Agent|(^|[^[:alnum:]])Pi([^[:alnum:]]|$)' \
  --exclude=validate.sh --exclude-dir=.git "$repo_dir" >/dev/null 2>&1; then
  printf 'runtime-specific Agent declaration found; keep the skill generic and recommend cc-switch\n' >&2
  exit 1
fi

if grep -R -n '~/.config/lecture-slides-to-obsidian\|XDG_CONFIG_HOME' "$skill_dir" \
  --exclude=README.md >/dev/null 2>&1; then
  printf 'external registry path found; runtime state must stay inside the skill\n' >&2
  exit 1
fi

if ! grep -q 'required-skills: "obsidian-markdown, obsidian-cli, obsidian-canvas-designer"' "$skill_dir/SKILL.md" || \
   ! grep -q 'required-skills: "json-canvas, obsidian-cli"' "$canvas_skill_dir/SKILL.md"; then
  printf 'skill prerequisite metadata is missing or out of sync\n' >&2
  exit 1
fi

if ! grep -q 'required-skills: "obsidian-markdown, obsidian-cli"' "$live_notes_skill_dir/SKILL.md" || \
   ! grep -q 'required-skills: "obsidian-markdown, obsidian-live-lecture-notes"' "$asr_skill_dir/SKILL.md"; then
  printf 'supplementary skill prerequisites are missing or out of sync\n' >&2
  exit 1
fi

if grep -q 'name: "obsidian"' "$asr_skill_dir/requirements/tools.yaml"; then
  printf 'ASR enricher must not require the Obsidian CLI tool\n' >&2
  exit 1
fi

if ! grep -q 'optional-skills: "slide-layout-refiner"' "$skill_dir/SKILL.md" || \
   ! grep -q 'requires-visual-input: "true"' "$layout_skill_dir/SKILL.md" || \
   ! grep -q 'enabled_by_default: false' "$skill_dir/requirements/skills.yaml"; then
  printf 'optional multimodal layout refinement contract is missing\n' >&2
  exit 1
fi

if ! grep -q 'name: "obsidian-canvas-designer"' "$skill_dir/requirements/skills.yaml" || \
   ! grep -q 'design_reference:' "$canvas_skill_dir/requirements/skills.yaml" || \
   ! grep -q 'name: "obsidian"' "$skill_dir/requirements/tools.yaml"; then
  printf 'Canvas delegation or Axton design prerequisites are missing\n' >&2
  exit 1
fi

if grep -R -n 'source_slides\|copy_source_into_course: true\|<course-folder>/Slides' \
  "$skill_dir" "$repo_dir/README.md" >/dev/null 2>&1; then
  printf 'source-original-in-vault contract found\n' >&2
  exit 1
fi

if ! grep -q 'required-services: "MinerU Precision API via official mineru-open-api CLI"' "$skill_dir/SKILL.md"; then
  printf 'service prerequisite metadata is missing or out of sync\n' >&2
  exit 1
fi

if grep -q 'mineru-pdf\|runtime_command' "$skill_dir/requirements/skills.yaml"; then
  printf 'local MinerU skill/runtime dependency is forbidden\n' >&2
  exit 1
fi

if ! grep -q 'name: "mineru-open-api"' "$skill_dir/requirements/tools.yaml" || \
   ! grep -q 'direct_http_calls: false' "$skill_dir/requirements/services.yaml"; then
  printf 'official MinerU CLI composition contract is missing or out of sync\n' >&2
  exit 1
fi

if grep -R -n '/api/v4/\|file-urls/batch\|extract-results/batch' \
  "$skill_dir/SKILL.md" "$skill_dir/references" "$skill_dir/config" >/dev/null 2>&1; then
  printf 'direct MinerU HTTP ownership is forbidden\n' >&2
  exit 1
fi

if grep -q 'language: "ch"\|is_ocr: false\|is_ocr: "confirm-per-document"' \
  "$skill_dir/requirements/services.yaml" "$skill_dir/config/pipeline.example.yaml"; then
  printf 'language and is_ocr must have no hard-coded request defaults\n' >&2
  exit 1
fi

if ! grep -q 'required_confirmation:' "$skill_dir/requirements/services.yaml"; then
  printf 'language/OCR confirmation contract is missing\n' >&2
  exit 1
fi

if ! grep -q 'persistence: "encrypted-at-rest"' "$skill_dir/requirements/services.yaml" || \
   ! grep -q 'file: "state/mineru-api-token.enc.json"' "$skill_dir/requirements/tools.yaml"; then
  printf 'encrypted token-store contract is missing or out of sync\n' >&2
  exit 1
fi

if ! grep -q 'repeated_user_confirmation: false' "$skill_dir/requirements/services.yaml"; then
  printf 'automatic credential reuse contract is missing\n' >&2
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1 || \
   ! openssl enc -list | grep -q 'aes-256-cbc'; then
  printf 'OpenSSL with aes-256-cbc is required\n' >&2
  exit 1
fi

if ! command -v obsidian >/dev/null 2>&1 || \
   [ ! -x "$skill_dir/scripts/plan-canvas-batch.py" ] || \
   [ ! -x "$canvas_skill_dir/scripts/canvas-render-qa.py" ] || \
   [ ! -x "$canvas_skill_dir/scripts/canvas-aesthetic-qa.py" ] || \
   [ ! -x "$canvas_skill_dir/scripts/recall-skeleton.py" ]; then
  printf 'Obsidian CLI and executable canvas-render-qa.py are required for local renderer QA\n' >&2
  exit 1
fi

if [ ! -x "$live_notes_skill_dir/scripts/apply-note-patches.py" ] || \
   [ ! -x "$asr_skill_dir/scripts/validate-enrichment-plan.py" ] || \
   [ ! -x "$layout_skill_dir/scripts/validate-layout-refinement.py" ]; then
  printf 'supplementary skill scripts must be executable\n' >&2
  exit 1
fi

if ! command -v security >/dev/null 2>&1 || \
   ! grep -q 'wrapping_key_backend: "macos-keychain"' "$skill_dir/requirements/tools.yaml"; then
  printf 'macOS Keychain security CLI is required for automatic token unlock\n' >&2
  exit 1
fi

if git -C "$repo_dir" ls-files --error-unmatch \
  'skills/lecture-slides-to-obsidian/state/mineru-api-token.enc.json' >/dev/null 2>&1; then
  printf 'encrypted runtime token file must not be tracked\n' >&2
  exit 1
fi

if ! git -C "$repo_dir" check-ignore -q \
  'skills/lecture-slides-to-obsidian/state/mineru-api-token.enc.json'; then
  printf 'encrypted runtime token file must be ignored\n' >&2
  exit 1
fi

python3 "$skill_dir/scripts/validate-output.py" \
  "$repo_dir/tests/fixtures/synthetic/valid-document-folder" \
  --fixture-mode \
  --report "$repo_dir/tests/fixtures/staging/conversion-report.md" >/dev/null

python3 -m unittest discover -s "$repo_dir/tests" -p 'test_*.py' >/dev/null

printf 'repository skeleton: ok\n'
