import type { TickRange } from './types';

/** Combines consecutive tick indexes into ranges while preserving their request order. */
export function getTickRanges(indexes: readonly number[]): TickRange[] {
    const ranges: TickRange[] = [];
    for (const index of indexes) {
        const previous = ranges.at(-1);
        if (previous && previous.endIndex + 1 === index) previous.endIndex = index;
        else ranges.push({ startIndex: index, endIndex: index });
    }
    return ranges;
}
