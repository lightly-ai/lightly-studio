export interface FramePositionRun {
    /** First frame position in the run. */
    readonly start: number;
    /** Last frame position in the run. */
    readonly end: number;
}

/**
 * Merges sorted, deduplicated frame positions into contiguous inclusive runs.
 *
 * A track lane draws one segment per run rather than one per frame, and the gaps between runs
 * are exactly the frame positions the track has no geometry for.
 */
export function toContiguousRuns(positions: readonly number[]): FramePositionRun[] {
    const runs: FramePositionRun[] = [];
    for (const position of positions) {
        const last = runs[runs.length - 1];
        if (last && position === last.end + 1) {
            runs[runs.length - 1] = { start: last.start, end: position };
        } else {
            runs.push({ start: position, end: position });
        }
    }
    return runs;
}
