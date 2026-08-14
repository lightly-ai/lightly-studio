#!/usr/bin/env bash
# Run the QA pipeline under a non-blocking host-level lock.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(dirname -- "$script_dir")"
state_dir="${QA_STATE_DIR:-/mnt/disks/qa}"

mkdir -p "$state_dir/logs" "$state_dir/work"

# Descriptor 9 keeps the lock for this process and releases it on every exit path.
exec 9>"$state_dir/qa-pipeline.lock"
if ! /usr/bin/flock --nonblock 9; then
    echo "$(date --iso-8601=seconds) QA pipeline already running; skipping."
    exit 0
fi

cd "$repo_dir"

echo "$(date --iso-8601=seconds) QA pipeline started."
"$repo_dir/.venv/bin/python" scripts/run_qa_pipeline.py \
    --apply \
    --cleanup-local-files \
    --narration-llm-model qwen3:4b \
    --db-file "$state_dir/qa-screen.db" \
    --destination "$state_dir/work"
echo "$(date --iso-8601=seconds) QA pipeline completed."
