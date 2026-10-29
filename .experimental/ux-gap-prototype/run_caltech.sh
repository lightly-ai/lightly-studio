#!/usr/bin/env bash
# Start a local LightlyStudio with the Caltech UX-run data, from any lightly-studio checkout.
#
#   run_caltech.sh prototype            # this branch, port 8001
#   run_caltech.sh main 8002 <checkout> # the main baseline, from a main worktree
#
# First run per name: builds the GUI (~5 min) and loads + embeds 5,000 images (~10 min).
# Later runs start in seconds. Pass --rebuild as the 4th argument to rebuild the GUI,
# --reload to reload the data, --prepare to build and load without starting the GUI.
set -euo pipefail
export PATH="/opt/homebrew/bin:$PATH"   # a stale ~/.cargo/bin/uv shadows the good one

name="${1:?name: prototype or main}"
port="${2:-8001}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
checkout="${3:-$(cd "$here/../.." && pwd)}"
flags="${4:-}"
data="$HOME/data/caltech-ux-run"
db_dir="$HOME/data/caltech-ux-run-dbs"
db="$db_dir/$name.db"
mkdir -p "$db_dir"

cd "$checkout/lightly_studio"
uv sync -q
dist="src/lightly_studio/dist_lightly_studio_view_app"
if [[ ! -f "$dist/index.html" || "$flags" == *--rebuild* ]]; then
    echo "Building the GUI for $checkout ..."
    make export-schema >/dev/null
    (cd ../lightly_studio_view && npm ci --silent && npm run generate-api-client >/dev/null         && npm run generate-language >/dev/null)
    rm -rf "$dist"
    make build-dirty-lightly_studio_view >/dev/null
fi
if [[ ! -f "$db" || "$flags" == *--reload* ]]; then
    echo "Loading Caltech data into $db ..."
    uv run python "$here/load_caltech.py" --data "$data" --db "$db"
fi
[[ "$flags" == *--prepare* ]] && exit 0
echo "LightlyStudio ($name) on http://localhost:$port"
uv run python "$here/serve.py" --db "$db" --port "$port"
