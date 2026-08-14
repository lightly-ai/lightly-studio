#!/usr/bin/env bash
# Periodic QA sampling wrapper for cron.
#
# Runs sample_gcs_review.py with --apply across every -qa bucket: 33% of each
# bucket's complete video triplets move to review, the rest to pool, and
# incomplete/stray files to incomplete. Safe to run repeatedly: source only ever
# holds files that arrived since the previous run.
#
# NOTE: runs as the invoking user's gcloud credentials. User credentials expire
# and need `gcloud auth login`; the durable fix is a service account (cloud step).
set -euo pipefail

export PATH="/home/nick/.local/bin:/snap/bin:/usr/bin:/bin:${PATH:-}"

repo_dir="/home/nick/repo/lightly-studio-1/lightly_studio"
cd "$repo_dir"

echo "=== $(date --iso-8601=seconds) sampler start ==="
uv run python scripts/sample_gcs_review.py --apply
echo "=== $(date --iso-8601=seconds) sampler done ==="
