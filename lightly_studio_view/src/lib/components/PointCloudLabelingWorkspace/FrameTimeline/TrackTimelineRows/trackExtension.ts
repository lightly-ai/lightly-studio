import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
import type { TrackRun } from './buildTrackRuns';

export type ExtendEdge = 'start' | 'end' | 'point';

/** Inclusive tick indices a track currently covers, from its first to its last run. */
export function getTrackExtent(runs: readonly TrackRun[]): { first: number; last: number } | null {
    const first = runs[0];
    const last = runs[runs.length - 1];
    return first && last ? { first: first.startIndex, last: last.endIndex } : null;
}

/** The tick boundary under a horizontal pointer position, clamped to the bar. */
export function tickIndexAt(clientX: number, bar: { left: number; width: number }, count: number) {
    if (bar.width <= 0 || count <= 0) return 0;
    const index = Math.floor(((clientX - bar.left) / bar.width) * count);
    return Math.min(count, Math.max(0, index));
}

/**
 * Where dragging a handle to `index` would put the track's coverage.
 */
export function proposeExtent(
    extent: { first: number; last: number },
    edge: ExtendEdge,
    index: number
): { first: number; last: number } {
    if (edge === 'point') {
        return { first: Math.min(index, extent.first), last: Math.max(index, extent.last) };
    }
    return edge === 'start'
        ? { first: Math.min(index, extent.last), last: extent.last }
        : { first: extent.first, last: Math.max(extent.first, index - 1) };
}

/** The tick numbers a proposed extent covers, or null when it changes nothing. */
export function toSeqNumberRange(
    ticks: readonly TickView[],
    extent: { first: number; last: number },
    proposed: { first: number; last: number }
): { start: number; end: number } | null {
    if (proposed.first === extent.first && proposed.last === extent.last) return null;
    const start = ticks[proposed.first];
    const end = ticks[proposed.last];
    return start && end ? { start: start.seq_number, end: end.seq_number } : null;
}
