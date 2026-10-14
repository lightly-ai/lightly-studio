import type { TickRange } from './types';

/** Converts completed tick indexes into sorted, contiguous ranges. */
export function getBufferedTickRanges(completed: ReadonlySet<number>): TickRange[] {
    const indexes = [...completed].sort((left, right) => left - right);
    const ranges: TickRange[] = [];
    for (const index of indexes) {
        const previous = ranges.at(-1);
        if (previous && previous.endIndex + 1 === index) previous.endIndex = index;
        else ranges.push({ startIndex: index, endIndex: index });
    }
    return ranges;
}
