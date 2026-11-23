const SECONDS_PER_MINUTE = 60;

/** Format a duration in seconds as `m:ss` (e.g. 65 → "1:05"). */
export function formatDuration(durationS: number): string {
    const totalSeconds = Math.max(0, Math.floor(durationS));
    const minutes = Math.floor(totalSeconds / SECONDS_PER_MINUTE);
    const seconds = totalSeconds % SECONDS_PER_MINUTE;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}
