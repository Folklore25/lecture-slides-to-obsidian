#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ "$1" != "--confirm" ]; then
  printf 'usage: %s --confirm\n' "$0" >&2
  exit 2
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
skill_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
state_dir="$skill_dir/state"

if [ ! -d "$state_dir" ] || [ "$(basename -- "$state_dir")" != "state" ]; then
  printf 'refusing to purge an unresolved state directory\n' >&2
  exit 1
fi

"$script_dir/token-store.py" delete --confirm >/dev/null

find "$state_dir" -maxdepth 1 -type f \
  \( -name 'course-registry.yaml' \
     -o -name 'course-registry.yaml.bak-*' \
     -o -name 'mineru-api-token.enc.json' \
     -o -name 'mineru-api-token.enc.json.bak-*' \
     -o -name '.mineru-token-*' \) \
  -delete

printf 'skill-owned registry, encrypted token, and Keychain wrapping key removed\n'
