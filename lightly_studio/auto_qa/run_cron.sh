#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(dirname -- "$script_dir")"
state_dir="${QA_STATE_DIR:-/mnt/disks/qa}"

mkdir -p "$state_dir/logs" "$state_dir/work"
exec 9>"$state_dir/qa-pipeline.lock"
/usr/bin/flock --nonblock 9 || exit 0

cd "$project_dir"
"$project_dir/.venv/bin/python" -m auto_qa \
    --apply \
    --cleanup-local-files \
    --download-workers 4 \
    --db-file "$state_dir/qa-screen.db" \
    --destination "$state_dir/work"
