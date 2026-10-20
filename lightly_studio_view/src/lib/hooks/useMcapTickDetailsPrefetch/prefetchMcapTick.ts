import type { QueryClient } from '@tanstack/svelte-query';
import { getTickDataOptions } from '$lib/hooks/useTickData/getTickDataOptions';
import { getTickDetailsOptions } from '$lib/hooks/useTickDetails/getTickDetailsOptions';

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
    await Promise.all([
        client.ensureQueryData(
            getTickDetailsOptions({ datasetId, sequenceId, seqNumber, displayFrameId })
        ),
        client.ensureQueryData(
            getTickDataOptions({ datasetId, sequenceId, seqNumber, displayFrameId })
        )
    ]);
}
