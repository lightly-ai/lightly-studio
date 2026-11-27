import { getTickRanges } from './getTickRanges';
import type { TickRange } from './types';

/** Converts completed tick indexes into sorted, contiguous ranges. */
export function getBufferedTickRanges(completed: ReadonlySet<number>): TickRange[] {
    const indexes = [...completed].sort((left, right) => left - right);
    return getTickRanges(indexes);
}
