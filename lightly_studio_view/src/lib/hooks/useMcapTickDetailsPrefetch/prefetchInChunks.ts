import type { PrefetchRangesRequest } from './types';
import { getBufferedTickRanges } from './getBufferedTickRanges';

interface PrefetchInChunksParams {
    /** Buffering session identifier. */
    requestId: string;
    /** Tick indexes to process in order. */
    indexes: readonly number[];
    /** Number of tick indexes per request. */
    chunkSize: number;
    /** Delay between completed chunks in milliseconds. */
    delayMs: number;
    /** Loads one chunk through the range executor. */
    prefetchRange: (request: PrefetchRangesRequest) => Promise<void>;
    /** Returns false when a newer schedule has replaced this one. */
    isCurrent: () => boolean;
}

const wait = (delayMs: number) => new Promise<void>((resolve) => setTimeout(resolve, delayMs));

/** Loads tick indexes in sequential chunks while allowing the current schedule to stop. */
export async function prefetchInChunks({
    requestId,
    indexes,
    chunkSize,
    delayMs,
    prefetchRange,
    isCurrent
}: PrefetchInChunksParams): Promise<void> {
    for (let offset = 0; offset < indexes.length; offset += chunkSize) {
        if (!isCurrent()) return;
        const chunk = indexes.slice(offset, offset + chunkSize);
        await prefetchRange({
            requestId,
            ranges: getBufferedTickRanges(new Set(chunk))
        });
        if (offset + chunkSize < indexes.length) await wait(delayMs);
    }
}
