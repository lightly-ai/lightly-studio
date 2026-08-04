/** Number of thumbnails shown per caption segment ribbon. */
export const DEFAULT_SEGMENT_SAMPLE_COUNT = 10;

interface UniformTimestampsParams {
    startTimeS: number;
    endTimeS: number;
    sampleCount: number;
}

/**
 * Timestamps evenly spread over `[startTimeS, endTimeS]`, both ends included.
 * A single sample lands in the middle of the interval.
 */
export function getUniformTimestamps({
    startTimeS,
    endTimeS,
    sampleCount
}: UniformTimestampsParams): number[] {
    if (sampleCount <= 0) return [];

    const start = Math.max(0, Math.min(startTimeS, endTimeS));
    const end = Math.max(0, Math.max(startTimeS, endTimeS));

    if (sampleCount === 1) return [start + (end - start) / 2];

    const step = (end - start) / (sampleCount - 1);
    return Array.from({ length: sampleCount }, (_, index) => start + index * step);
}

/** Format a timestamp in seconds as `m:ss.d` (e.g. 65.42 → "1:05.4"). */
export function formatTimestampS(timeS: number): string {
    const clamped = Math.max(0, timeS);
    const minutes = Math.floor(clamped / 60);
    const seconds = clamped - minutes * 60;
    return `${minutes}:${seconds.toFixed(1).padStart(4, '0')}`;
}
