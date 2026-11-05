#!/usr/bin/env bash
# Logs the runner hardware (`start`) and summarizes the load during the job (`report`).
# The `RUNNER_INFO` and `RUNNER_LOAD` lines have a fixed format, so that scripts can
# collect them from the job logs.
set -euo pipefail

VMSTAT_LOG="${RUNNER_TEMP:-/tmp}/runner-info-vmstat.log"
SAMPLE_SECONDS=5

start() {
    local cpu memory disk
    cpu=$(lscpu | sed -n 's/^Model name: *//p' | head -n 1)
    memory=$(free -h | awk '/^Mem:/ {print $2}')
    disk=$(df -h --output=avail "${GITHUB_WORKSPACE:-.}" | tail -n 1 | tr -d ' ')
    local info="cpu=\"${cpu}\" vcpus=$(nproc) memory=${memory} disk_free=${disk} kernel=$(uname -r)"

    echo "RUNNER_INFO ${info}"
    echo "::group::Runner hardware details"
    lscpu
    free -h
    df -h
    echo "::endgroup::"
    echo "**Runner:** ${info}" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"

    # Runs in the background until the runner ends the job.
    nohup vmstat -n -t -S M "${SAMPLE_SECONDS}" > "${VMSTAT_LOG}" 2>&1 &
}

report() {
    if [[ ! -s "${VMSTAT_LOG}" ]]; then
        echo "No samples found, did the start step run?"
        return
    fi
    local load
    load=$(summarize < "${VMSTAT_LOG}")

    echo "RUNNER_LOAD ${load}"
    echo "::group::CPU, memory and disk samples (every ${SAMPLE_SECONDS}s)"
    cat "${VMSTAT_LOG}"
    echo "::endgroup::"
    echo "**Load:** ${load}" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
}

# Reads `vmstat` output and prints averages and extremes.
# - busy: CPU time used by processes (user + system).
# - iowait: CPU time spent waiting for the disk.
# - steal: CPU time taken by other virtual machines on the same host.
# - max_queue: most processes waiting for a CPU at the same time.
# - min_available: least free memory, including caches.
# - max_swap: most memory moved to swap.
summarize() {
    awk '
        NR == 2 { for (i = 1; i <= NF; i++) col[$i] = i; next }
        # The first sample is the average since boot, skip it.
        NR <= 3 || $1 !~ /^[0-9]+$/ { next }
        {
            n++
            busy += $col["us"] + $col["sy"]
            iowait += $col["wa"]
            steal += $col["st"]
            if ($col["st"] > max_steal) max_steal = $col["st"]
            if ($col["r"] > max_queue) max_queue = $col["r"]
            available = $col["free"] + $col["buff"] + $col["cache"]
            if (n == 1 || available < min_available) min_available = available
            if ($col["swpd"] > max_swap) max_swap = $col["swpd"]
        }
        END {
            if (n == 0) { print "samples=0"; exit }
            printf "samples=%d busy=%.0f%% iowait=%.0f%% steal=%.0f%% max_steal=%d%% ", n, busy / n, iowait / n, steal / n, max_steal
            printf "max_queue=%d min_available=%dMB max_swap=%dMB\n", max_queue, min_available, max_swap
        }
    '
}

case "${1:-}" in
    start) start ;;
    report) report ;;
    *) echo "Usage: $0 start|report" >&2; exit 1 ;;
esac
