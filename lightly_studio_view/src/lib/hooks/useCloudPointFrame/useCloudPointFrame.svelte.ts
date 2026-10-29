import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';
import { getTickDataOptions } from '$lib/hooks/useTickData/getTickDataOptions';
import type { TickData } from '$lib/hooks/useTickData/fetchTickData';
import { createAccumulatedFrameSelector } from './createAccumulatedFrameSelector';
import type { CloudPointFrame, CloudPointFrameParams } from './types';

interface UseCloudPointFrameReturn {
    /** Query result for the merged point-cloud frame. */
    query: CreateQueryResult<CloudPointFrame, Error>;
}

/**
 * Merges the point clouds of the selected lidar channels from the shared tick-data query,
 * so changing the selection does not refetch. A point cloud that cannot be expressed in
 * `displayFrameId` stays in its sensor frame, which the `frameId` of its channel shows.
 *
 * When `accumulationTickNumbers` contains more than one tick, frames from all ticks are
 * fetched in parallel and merged into a single batch for display.
 */
export const useCloudPointFrame = (
    getParams: () => CloudPointFrameParams
): UseCloudPointFrameReturn => {
    const client = useQueryClient();
    const selectFrame = createAccumulatedFrameSelector();
    const query = createQuery(() => {
        const {
            datasetId,
            sequenceId,
            seqNumber,
            displayFrameId,
            selectedChannelIds,
            accumulationTickNumbers
        } = getParams();
        const tickNumbers = [...new Set(accumulationTickNumbers ?? [seqNumber])];
        const tickQueries = tickNumbers.map((tick) =>
            getTickDataOptions({ datasetId, sequenceId, seqNumber: tick, displayFrameId })
        );
        return {
            queryKey: [
                'cloud-point-frame',
                datasetId,
                sequenceId,
                tickNumbers,
                displayFrameId ?? '',
                selectedChannelIds ?? []
            ],
            queryFn: () =>
                Promise.all(tickQueries.map((options) => client.ensureQueryData(options))),
            select: (data: TickData[]) => selectFrame(data, selectedChannelIds),
            // Skip fetching until the tick is known and at least one lidar is selected.
            enabled: Boolean(datasetId && sequenceId && (selectedChannelIds?.length ?? 1)),
            // Preserve the mounted scene and its camera while the next window is loading.
            placeholderData: (previous: TickData[] | undefined) => previous
        };
    });
    return { query };
};
