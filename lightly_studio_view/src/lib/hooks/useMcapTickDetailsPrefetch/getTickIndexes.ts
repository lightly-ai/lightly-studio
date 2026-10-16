import type { TickRange } from './types';

/** Expands inclusive ranges into unique, valid tick indexes. */
export function getTickIndexes(ranges: readonly TickRange[], tickCount: number): number[] {
    const indexes = new Set<number>();
    for (const range of ranges) {
        const start = Math.max(0, range.startIndex);
        const end = Math.min(tickCount - 1, range.endIndex);
        for (let index = start; index <= end; index += 1) indexes.add(index);
    }
    return [...indexes];
}
