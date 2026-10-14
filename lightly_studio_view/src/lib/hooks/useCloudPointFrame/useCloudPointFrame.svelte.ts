import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import { getTickDataOptions } from '$lib/hooks/useTickData/getTickDataOptions';
import type { TickData } from '$lib/hooks/useTickData/fetchTickData';
import { mergeCloudPointFrames } from './mergeCloudPointFrames';
import type { CloudPointFrame, CloudPointFrameParams } from './types';

interface UseCloudPointFrameReturn {
    /** Query result for the merged point-cloud frame. */
    query: CreateQueryResult<CloudPointFrame, Error>;
}

/**
 * Loads a tick's sensor data and merges the point clouds of the selected lidar channels.
 *
 * The tick data is one cached request shared with the camera strip and the prefetch, so
 * changing the selection does not refetch. A point cloud that cannot be expressed in
 * `displayFrameId` stays in its sensor frame, which the `frameId` of its channel shows.
 * Accepts a getter (thunk) so the query stays reactive to parameter changes.
 *
 * @param getParams - Reactive getter for the tick, the display frame, and the selection.
 * @returns The TanStack Query result exposing the merged cloud point frame.
 */
export const useCloudPointFrame = (
    getParams: () => CloudPointFrameParams
): UseCloudPointFrameReturn => {
    const query = createQuery(() => {
        const { datasetId, sequenceId, seqNumber, displayFrameId, selectedChannelIds } =
            getParams();
        return {
            ...getTickDataOptions({ datasetId, sequenceId, seqNumber, displayFrameId }),
            select: (data: TickData) => mergeSelected(data, selectedChannelIds),
            // Skip fetching until the tick is known and at least one lidar is selected.
            enabled: Boolean(datasetId && sequenceId && (selectedChannelIds?.length ?? 1)),
            // Preserve the mounted scene and its camera while the next tick is loading.
            placeholderData: (previous: TickData | undefined) => previous
        };
    });
    return { query };
};

function mergeSelected(data: TickData, selectedChannelIds?: number[]): CloudPointFrame {
    const [first, ...others] = data.pointClouds.filter(
        (frame) => selectedChannelIds === undefined || selectedChannelIds.includes(frame.channelId)
    );
    if (!first) throw new Error('No point cloud channels to load.');
    return mergeCloudPointFrames([first, ...others]);
}
