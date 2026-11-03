import type { TickRange } from './types';

interface GetMcapTickPrefetchRangeParams {
    /** Zero-based index of the currently visible tick. */
    activeIndex: number;
    /** Number of ticks in the sequence. */
    tickCount: number;
    /** Number of ticks to prefetch, including the active tick. */
    prefetchTickCount: number;
    /** Neighboring ticks needed on each side of an accumulated frame. */
    accumulationRadius?: number;
}

/** Returns the forward-looking range that should be prefetched for the active tick. */
export function getMcapTickPrefetchRange({
    activeIndex,
    tickCount,
    prefetchTickCount,
    accumulationRadius = 0
}: GetMcapTickPrefetchRangeParams): TickRange[] {
    if (activeIndex < 0 || activeIndex >= tickCount || tickCount === 0) return [];

    const count = Math.max(1, Math.floor(prefetchTickCount));
    return [
        {
            startIndex: Math.max(0, activeIndex - accumulationRadius),
            endIndex: Math.min(tickCount - 1, activeIndex + count - 1 + accumulationRadius)
        }
    ];
}
