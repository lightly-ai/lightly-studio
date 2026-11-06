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

type RunRequest = <T>(request: () => Promise<T>) => Promise<T>;

/**
 * Prefetches the cached data needed to render one MCAP tick: its details and its sensor data.
 *
 * The details request starts at once. The data request starts through `runDataRequest`, so the
 * caller can limit how many data requests run at once.
 */
export async function prefetchMcapTick(
    /** Query client that owns the visible workspace cache. */
    client: QueryClient,
    { datasetId, sequenceId, seqNumber, displayFrameId }: McapTickPrefetchParams,
    /** Starts the tick-data request. Defaults to starting it at once. */
    runDataRequest: RunRequest = (request) => request()
): Promise<void> {
    await Promise.all([
        client.ensureQueryData(
            getTickDetailsOptions({ datasetId, sequenceId, seqNumber, displayFrameId })
        ),
        runDataRequest(() =>
            client.ensureQueryData(
                getTickDataOptions({ datasetId, sequenceId, seqNumber, displayFrameId })
            )
        )
    ]);
}
