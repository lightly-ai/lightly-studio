import type { QueryClient } from '@tanstack/svelte-query';
import { getTickDataOptions } from '$lib/hooks/useTickData/getTickDataOptions';
import { getTickDetailsOptions } from '$lib/hooks/useTickDetails/getTickDetailsOptions';

const PREFETCH_TIMEOUT_MS = 30_000;

interface McapTickPrefetchParams {
    /** Dataset that owns the sequence. */
    datasetId: string;
    /** Sequence whose tick should be prefetched. */
    sequenceId: string;
    /** Zero-based tick position in the sequence. */
    seqNumber: number;
    /** Optional target frame for the annotations and the point clouds. */
    displayFrameId?: string;
}

/** Prefetches the cached data needed to render one MCAP tick: its details and its sensor data. */
export async function prefetchMcapTick(
    /** Query client that owns the visible workspace cache. */
    client: QueryClient,
    { datasetId, sequenceId, seqNumber, displayFrameId }: McapTickPrefetchParams
): Promise<void> {
    const details = getTickDetailsOptions({ datasetId, sequenceId, seqNumber, displayFrameId });
    const data = getTickDataOptions({ datasetId, sequenceId, seqNumber, displayFrameId });
    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    const timeout = new Promise<never>((_, reject) => {
        timeoutId = setTimeout(() => {
            reject(new Error('Loading frame timed out. Please try again.'));
            // Cancel the cached requests so a retry starts fresh rather than joining a hung fetch.
            void client.cancelQueries({ queryKey: details.queryKey, exact: true });
            void client.cancelQueries({ queryKey: data.queryKey, exact: true });
        }, PREFETCH_TIMEOUT_MS);
    });
    try {
        await Promise.race([
            Promise.all([client.ensureQueryData(details), client.ensureQueryData(data)]),
            timeout
        ]);
    } finally {
        clearTimeout(timeoutId);
    }
}
