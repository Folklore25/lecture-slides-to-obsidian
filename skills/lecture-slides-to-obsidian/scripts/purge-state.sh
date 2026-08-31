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

find "$state_dir" -maxdepth 1 -type f \
  \( -name 'course-registry.yaml' -o -name 'course-registry.yaml.bak-*' \) \
  -delete

printf 'skill-owned course registry state removed\n'
