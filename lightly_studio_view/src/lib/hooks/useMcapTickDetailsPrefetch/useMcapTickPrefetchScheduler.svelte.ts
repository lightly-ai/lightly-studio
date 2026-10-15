import { onDestroy } from 'svelte';
import { getTickIndexes } from './getTickIndexes';
import { prefetchInChunks } from './prefetchInChunks';
import { useMcapTickDetailsPrefetch } from './useMcapTickDetailsPrefetch.svelte';
import type { McapTickPrefetchSchedulerParams } from './types';

const DEFAULT_CHUNK_SIZE = 10;
const DEFAULT_DELAY_MS = 200;

/**
 * Gradually fills the cache with ticks that may be needed soon.
 *
 * Think of this hook as a small delivery worker:
 * 1. The component says which tick range should be loaded.
 * 2. This hook splits the range into small batches.
 * 3. The executor loads every batch with limited concurrency.
 * 4. A short delay prevents background loading from taking all network capacity.
 */
export const useMcapTickPrefetchScheduler = ({
    getDatasetId,
    getSequenceId,
    getDisplayFrameId,
    getTicks,
    getRequestId,
    getRanges,
    getChunkSize = () => DEFAULT_CHUNK_SIZE,
    getDelayMs = () => DEFAULT_DELAY_MS
}: McapTickPrefetchSchedulerParams) => {
    const executor = useMcapTickDetailsPrefetch({
        getDatasetId,
        getSequenceId,
        getDisplayFrameId,
        getTicks
    });
    // This version changes only when the buffering session changes. Moving the look-ahead window
    // during playback must not cancel chunks that are already being loaded.
    let sessionVersion = 0;
    // The same request ID means “continue filling the same buffer”.
    // A new request ID means “start a different buffer”, such as after a jump.
    let currentRequestId: string | undefined;

    $effect(() => {
        const requestId = getRequestId();
        if (currentRequestId !== undefined && currentRequestId !== requestId) {
            // A jump or a new sequence makes the old buffer irrelevant.
            sessionVersion += 1;
            executor.cancel();
        }
        currentRequestId = requestId;
        const currentSessionVersion = sessionVersion;

        // Convert ranges like [{ startIndex: 2, endIndex: 5 }] into [2, 3, 4, 5].
        void prefetchInChunks({
            requestId,
            indexes: getTickIndexes(getRanges(), getTicks().length),
            // Keep these values safe even if a caller provides 0 or a negative number.
            chunkSize: Math.max(1, Math.floor(getChunkSize())),
            delayMs: Math.max(0, getDelayMs()),
            prefetchRange: executor.prefetchRanges,
            // A moving range in the same session may start another plan, but it must not stop
            // this one. Only a new request ID invalidates the previous session.
            isCurrent: () => currentSessionVersion === sessionVersion
        });
    });

    const cancel = () => {
        // Stop delayed chunk loops as well as work already queued in the executor.
        sessionVersion += 1;
        executor.cancel();
    };
    onDestroy(cancel);

    return {
        cancel,
        get bufferedRanges() {
            return executor.bufferedRanges;
        },
        get errors() {
            return executor.errors;
        }
    };
};
