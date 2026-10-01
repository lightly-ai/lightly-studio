/** Format a duration in seconds as `m:ss` (e.g. 65 → "1:05"). */
export function formatTime(timeS: number): string {
    const totalSeconds = Math.max(0, Math.floor(timeS));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

/** Clamp a percentage to the 0–100 range. */
export function clampPercent(value: number): number {
    return Math.min(100, Math.max(0, value));
}

/** Map a pointer's x position over the track to a time in `[0, durationS]`. */
export function timeFromClientX(clientX: number, rect: DOMRect, durationS: number): number {
    if (durationS <= 0) return 0;
    const ratio = rect.width > 0 ? (clientX - rect.left) / rect.width : 0;
    return Math.min(durationS, Math.max(0, ratio * durationS));
}
